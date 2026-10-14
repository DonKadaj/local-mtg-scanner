#!/usr/bin/env python3
"""Replay a folder of card photos through identify_card() and score it.

Measures the recognition rate on a fixed test set, so every change to the
OCR / matching code can be compared with the previous run.

1. Collect photos: start the server with CARD_TRACKER_SAVE_SCANS=test_cards
   and scan each test card once in single-photo mode (or drop .jpg/.png
   files into test_cards/ yourself).
2. python tools/bench_scan.py --init
   Writes test_cards/labels.csv, pre-filled with what the app matched.
   Open it, fix set / number / lang so each row is the TRUE card, then
   run --init again: the "name" column is refreshed from set + number,
   so you can check the corrections (the file must be closed in Excel).
3. python tools/bench_scan.py [--offline]
   Re-runs recognition on every labelled photo with the current code,
   prints a summary and writes test_cards/results/results-<date>.csv.

Labels use ";" as separator so Excel (French locale) opens them directly.
"""
import argparse
import csv
import json
import os
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import server  # noqa: E402

IMAGE_EXT = (".jpg", ".jpeg", ".png")
FIELDS = ["file", "set", "number", "lang", "foil", "name", "title_read", "note"]
VERDICTS = [
    ("exact", "exact print (right set + number)"),
    ("name", "right card, wrong or unknown printing"),
    ("wrong", "wrong card"),
    ("none", "no match"),
]


def sniff_delimiter(path):
    """";" by default, "," if the file was saved that way by another editor."""
    if not os.path.exists(path):
        return ";"
    with open(path, encoding="utf-8-sig") as f:
        header = f.readline()
    return ";" if header.count(";") >= header.count(",") else ","


def read_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f, delimiter=sniff_delimiter(path)))


def write_csv(path, fields, rows, delimiter=";"):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields, delimiter=delimiter, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def init_labels(folder, labels_path):
    """Create or extend labels.csv with every photo not labelled yet."""
    delimiter = sniff_delimiter(labels_path)
    rows = read_csv(labels_path) if os.path.exists(labels_path) else []
    known = {r["file"] for r in rows}
    added = 0
    for name in sorted(os.listdir(folder)):
        if not name.lower().endswith(IMAGE_EXT) or name in known:
            continue
        saved = {}
        side = os.path.join(folder, os.path.splitext(name)[0] + ".json")
        if os.path.exists(side):  # result saved by the server at scan time
            with open(side, encoding="utf-8") as f:
                saved = json.load(f) or {}
        guess = saved.get("match") or {}
        rows.append({"file": name,
                     "set": (guess.get("set_code") or "").lower(),
                     "number": guess.get("collector_number") or "",
                     "lang": "fr", "foil": "no", "title_read": saved.get("ocr_guess") or "",
                     "note": ""})
        added += 1
    # (Re)fill the English name from set + number, so corrections show up.
    server.load_local("mtg")
    for r in rows:
        side = os.path.join(folder, os.path.splitext(r["file"])[0] + ".json")
        if not r.get("title_read") and os.path.exists(side):
            with open(side, encoding="utf-8") as f:
                r["title_read"] = (json.load(f) or {}).get("ocr_guess") or ""
        card = None
        if r.get("set") and r.get("number"):
            card = server.local_exact_match(r["set"].strip().lower(), r["number"].strip())
        if card:
            r["name"] = card["name"]
        elif r.get("set"):
            r["name"] = "?? unknown set/number"
        # no set (old card): keep the name typed by hand, it is the reference
    write_csv(labels_path, FIELDS, rows, delimiter)
    print("%d photo(s) added to %s (%d in total)." % (added, labels_path, len(rows)))
    print("Check every row: set / number / lang must describe the TRUE card.")
    print("Run --init again after editing to refresh the names.")


def run_bench(folder, labels_path, offline):
    if not os.path.exists(labels_path):
        sys.exit("No %s yet: run with --init first." % labels_path)
    if not server.load_local("mtg"):
        print("Warning: offline database not downloaded; expected names unknown.")
    if offline:
        server.provider_for("mtg").has_api = False
    print("OCR backend: %s · Tesseract langs: %s · API: %s\n" % (
        server.detect_ocr_backend(), server.TESS_LANGS, "off" if offline else "on"))

    # Keep the OCR lines of the last call so we can report what was read.
    last = {}
    real_ocr = server.ocr_image

    def spy_ocr(path, attempts=2):
        last["lines"] = real_ocr(path, attempts)
        return last["lines"]
    server.ocr_image = spy_ocr

    out, counts = [], Counter()
    groups = defaultdict(Counter)  # ("lang", "fr") / ("foil", "foil") → verdicts
    for r in read_csv(labels_path):
        path = os.path.join(folder, r["file"])
        name_only = not r.get("set") and r.get("name", "").strip()
        if not os.path.exists(path) or not (name_only or (r.get("set") and r.get("number"))):
            print("skip  %s (missing photo or label)" % r["file"])
            continue
        want_set, want_num = r["set"].strip().lower(), server._norm_num(r["number"].strip())
        if name_only:  # old card with no set printed: only the name can be checked
            want = {"name": r["name"].strip()}
        else:
            want = server.local_exact_match(want_set, want_num) or {}
        last.clear()
        t0 = time.time()
        try:
            res = server.identify_card(path)
            err = ""
        except Exception as e:  # keep going: one bad photo must not stop the run
            res, err = {}, str(e)
        secs = time.time() - t0
        lines = last.get("lines") or []
        read = res.get("read")  # what the server read (incl. the corner reader)
        if read is not None:
            read_set, read_num = read.get("set"), read.get("number")
        else:
            read_set, read_num = server.parse_print_info(lines) if lines else (None, None)
        m = res.get("match") or {}
        got_set = (m.get("set_code") or "").lower()
        got_num = server._norm_num(m.get("collector_number") or "")
        if not m:
            verdict = "none"
        elif (got_set, got_num) == (want_set, want_num):
            verdict = "exact"
        elif want and server._norm_name(m.get("name", "")) == server._norm_name(want.get("name", "")):
            verdict = "name"
        else:
            verdict = "wrong"
        counts[verdict] += 1
        lang = (r.get("lang") or "?").strip().lower()
        foil = "foil" if (r.get("foil") or "").strip().lower() in ("yes", "y", "oui", "o", "1", "x", "foil") else "non-foil"
        if name_only:  # no set printed: only the number can be checked
            bottom_ok = bool(read_num) and server._norm_num(read_num) == want_num
        else:
            bottom_ok = (read_set, server._norm_num(read_num or "")) == (want_set, want_num)
        for g in (("lang", lang), ("foil", foil)):
            groups[g][verdict] += 1
            groups[g]["bottom_ok"] += bottom_ok
        out.append({
            "file": r["file"], "lang": lang, "foil": foil, "note": r.get("note", ""),
            "expected": "%s #%s %s" % (want_set.upper() or "(no set)", want_num, want.get("name", "?")),
            "verdict": verdict,
            "matched": "%s #%s %s" % (got_set.upper(), got_num, m.get("name", "")) if m else "",
            "method": res.get("method") or "",
            "title_read": res.get("ocr_guess") or "",
            "set_read": read_set or "",
            "number_read": read_num or "",
            "bottom_line_ok": "yes" if bottom_ok else "no",
            "seconds": "%.1f" % secs,
            "error": err,
        })
        print("%-5s %-28s %-8s read: %s #%s · title: %s" % (
            verdict, r["file"][:28], out[-1]["method"],
            (read_set or "-").upper(), read_num or "-", (res.get("ocr_guess") or "-")[:30]))

    n = len(out)
    if not n:
        sys.exit("Nothing to score.")
    print("\n=== %d card(s) ===" % n)
    for key, label in VERDICTS:
        print("%-6s %3d  %5.1f%%  %s" % (key, counts[key], 100.0 * counts[key] / n, label))
    ok_bottom = sum(1 for o in out if o["bottom_line_ok"] == "yes")
    print("bottom line read correctly: %d/%d" % (ok_bottom, n))
    for kind in ("lang", "foil"):
        subs = sorted((v, c) for (k, v), c in groups.items() if k == kind)
        if len(subs) < 2:
            continue
        for value, c in subs:
            tot = sum(c[k] for k, _ in VERDICTS)
            print("  %-9s exact %d/%d · bottom line read %d/%d" % (
                value, c["exact"], tot, c["bottom_ok"], tot))

    res_dir = os.path.join(folder, "results")
    os.makedirs(res_dir, exist_ok=True)
    res_path = os.path.join(res_dir, "results-%s.csv" % datetime.now().strftime("%Y%m%d-%H%M"))
    write_csv(res_path, list(out[0].keys()), out)
    print("\nDetails: %s" % res_path)


def main():
    if hasattr(sys.stdout, "reconfigure"):  # Windows console: avoid encode errors
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("folder", nargs="?", default=os.path.join(ROOT, "test_cards"))
    ap.add_argument("--init", action="store_true", help="create / extend labels.csv")
    ap.add_argument("--offline", action="store_true", help="local database only, no Scryfall API")
    a = ap.parse_args()
    labels = os.path.join(a.folder, "labels.csv")
    if a.init:
        init_labels(a.folder, labels)
    else:
        run_bench(a.folder, labels, a.offline)


if __name__ == "__main__":
    main()
