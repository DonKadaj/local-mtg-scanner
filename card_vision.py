"""Optional card-image helpers for Magic scans (needs OpenCV).

Install with:  pip install opencv-python-headless
Without OpenCV, server.py simply keeps its whole-photo OCR.

The whole-photo OCR misses the small collector line at the bottom of the
card (set code, language, rarity, collector number). Here we find the card
in the photo, straighten it, cut the bottom strip, enlarge it and OCR that
strip on its own. Several image variants are tried; a reading is accepted
as soon as the set + number exist in the card database.

Magic only: the strip position matches the Magic card frame.
"""
import os
import re
import subprocess
import tempfile

import cv2
import numpy as np

CARD_RATIO = 88 / 63  # height / width of a Magic card
WARP_WIDTH = 1000
# where the collector lines sit, as fractions of the card height
STRIPS = ((0.905, 0.99), (0.925, 1.0), (0.885, 0.97))

# Language codes printed after the set code ("HOB • FR", "HOB★FR").
LANG_RE = re.compile(r"(?<![A-Z])(EN|FR|DE|IT|ES|PT|JA|JP|KO|RU|ZH|CS|CT|PH)(?![A-Z])")
# Rarity letter + 4-digit number, very tolerant to OCR misreads:
# "U 0052", "c 0100", "L o188", "Uu 0052", "c 004s", "R0015" → "ROOIS".
RARITY_NUM_RE = re.compile(r"(?:^|\s)[A-Za-z]{1,2}\s*([0-9OoQDIl|Ss©¢B]{4,5})(?![0-9A-Za-z])")
# Older cards: "40/350" (a power/toughness box like "3/2" has a small total).
OLD_NUM_RE = re.compile(r"\b(\d{1,3})\s*/\s*(\d{2,3})\b")
DIGIT_FIX = str.maketrans("OoQDIl|Ss©¢B", "000011155008")
SET_TOKEN_RE = re.compile(r"\b([A-Z][A-Z0-9]{2,4})")


def find_card(img):
    """Return the 4 corners of the card in the photo, or None."""
    h, w = img.shape[:2]
    s = 800.0 / max(h, w)
    small = cv2.resize(img, (int(w * s), int(h * s)))
    area = small.shape[0] * small.shape[1]
    gray = cv2.GaussianBlur(cv2.cvtColor(small, cv2.COLOR_BGR2GRAY), (5, 5), 0)
    best, best_area = None, 0
    # several edge settings: dark borders on a dark table need softer ones
    for lo, hi, grow in ((50, 150, 1), (30, 100, 1), (30, 100, 2), (80, 200, 1)):
        edges = cv2.dilate(cv2.Canny(gray, lo, hi), np.ones((3, 3), np.uint8),
                           iterations=grow)
        contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        for c in contours:
            a = cv2.contourArea(c)
            if a < 0.2 * area or a > 0.97 * area or a <= best_area:
                continue
            hull = cv2.convexHull(c)
            quad = cv2.approxPolyDP(hull, 0.02 * cv2.arcLength(hull, True), True)
            if len(quad) != 4:
                continue
            rw, rh = cv2.minAreaRect(quad)[1]
            if min(rw, rh) == 0 or abs(max(rw, rh) / min(rw, rh) - CARD_RATIO) > 0.08:
                continue
            best, best_area = quad.reshape(4, 2) / s, a
    return best  # the largest card-shaped outline (inner frames are smaller)


def _order(pts):
    pts = np.array(pts, dtype="float32")
    s, d = pts.sum(1), np.diff(pts, axis=1).ravel()
    return np.array([pts[np.argmin(s)], pts[np.argmin(d)],
                     pts[np.argmax(s)], pts[np.argmax(d)]], dtype="float32")


def straighten(img, corners):
    """Warp the card to an upright WARP_WIDTH-wide image."""
    w, h = WARP_WIDTH, int(WARP_WIDTH * CARD_RATIO)
    dst = np.array([[0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1]], dtype="float32")
    tl, tr, br, bl = _order(corners)
    if np.linalg.norm(tr - tl) > np.linalg.norm(bl - tl):  # card lying sideways
        tl, tr, br, bl = bl, tl, tr, br
    m = cv2.getPerspectiveTransform(np.array([tl, tr, br, bl]), dst)
    return cv2.warpPerspective(img, m, (w, h))


def _ocr(gray, tess_langs):
    fd, path = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    try:
        cv2.imwrite(path, gray)
        out = subprocess.run(["tesseract", path, "stdout", "-l", tess_langs, "--psm", "6"],
                             capture_output=True, text=True, timeout=30)
        return out.stdout
    finally:
        os.unlink(path)


def _edit_distance(a, b):
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def parse_collector_text(text, sets_for_number):
    """Guesses (set, number, lang, doubt) found in the corner text.

    sets_for_number(number) -> set codes (lowercase) that have a card with
    that collector number. A number is only kept with a set that really has
    it, the set being the one closest to what was read (1 typo allowed).
    An old card with no set code gives (None, number, None, 0).
    """
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    nums, first_num_line = [], None
    for i, ln in enumerate(lines):
        found = []
        for raw in RARITY_NUM_RE.findall(ln):
            raw = raw[-4:]  # the number is 4 digits; a 5th char is noise
            n = raw.translate(DIGIT_FIX)
            if n.isdigit() and 0 < int(n) < 2000:
                found.append((str(int(n)), sum(not ch.isdigit() for ch in raw)))
        found += [(a, 0) for a, total in OLD_NUM_RE.findall(ln) if int(total) >= 20]
        if found and first_num_line is None:
            first_num_line = i
        nums += found
    # the set code starts the line printed under the number: "HOB*FR  artist"
    tokens, lang = [], None
    for ln in lines[(first_num_line or 0) + (first_num_line is not None):]:
        up = re.sub(r"^[^A-Z0-9]+", "", ln.upper())
        m = SET_TOKEN_RE.match(up)
        if not m:
            continue
        tok = m.group(1)
        tokens += [(tok[:k], len(tokens)) for k in (3, 4, 5)]
        m = LANG_RE.search(up[3:].replace("FER", "FR"))
        if m and lang is None:
            lang = m.group(1)
    guesses = []
    for n, fixed in dict.fromkeys(nums):
        best = None
        for code in sets_for_number(n):
            for tok, line in tokens:  # closest code, then the highest line
                d = _edit_distance(code.upper(), tok)
                if d <= 1 and (best is None or (d, line) < best[:2]):
                    best = (d, line, code)
        if best:  # doubt = set typos + digits guessed from letters
            guesses.append((best[2], n, lang, best[0] + fixed))
    if nums and not tokens:  # old card with no set code printed
        guesses.append((None, nums[0][0], None, nums[0][1]))
    return guesses


def read_collector_line(image_path, sets_for_number, tess_langs="eng"):
    """(set, number, lang) read from the card's bottom-left corner.

    The corner is OCR'd in three image variants and the guesses are voted.
    Returns (None, number, None) for an old card with no set code, and
    (None, None, None) when nothing usable is found.
    """
    img = cv2.imread(image_path)
    if img is None:
        return None, None, None
    corners = find_card(img)
    card = straighten(img, corners) if corners is not None else img
    h, w = card.shape[:2]
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(4, 8))
    variants = (  # white text on a black border → dark text on light
        lambda g: 255 - clahe.apply(g),
        lambda g: cv2.threshold(255 - clahe.apply(g), 0, 255,
                                cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1],
        lambda g: 255 - g,
    )
    votes, langs = {}, {}
    for top, bottom in STRIPS:  # frames differ a little: try a few positions
        corner = cv2.cvtColor(card[int(h * top):int(h * bottom), int(w * 0.02):int(w * 0.55)],
                              cv2.COLOR_BGR2GRAY)
        corner = cv2.resize(corner, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
        for make in variants if top == STRIPS[0][0] else variants[:2]:
            for s, n, lang, doubt in parse_collector_text(_ocr(make(corner), tess_langs),
                                                          sets_for_number):
                count, best_doubt = votes.get((s, n), (0, 99))
                votes[(s, n)] = (count + 1, min(best_doubt, doubt))
                if lang:
                    langs.setdefault((s, n), lang)
        if any(s for s, _ in votes):
            break
    if not votes:
        return None, None, None
    complete = [k for k in votes if k[0]] or list(votes)
    # most votes first, then the least doubtful reading
    s, n = max(complete, key=lambda k: (votes[k][0], -votes[k][1]))
    return s, n, langs.get((s, n))
