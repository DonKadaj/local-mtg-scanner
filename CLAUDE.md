# Project: MTG Scanning Station (Maker project)

## Context
Maker project: turn an existing Magic: The Gathering card scanner into a card scanning and inventory station (mechanics, electronics, 3D printing, software).
Software base: fork of `McDandle/local-mtg-scanner` (Local TCG Scanner).
Chosen for its web interface (inventory, sorting by set/collection, card images) and because it runs on both Windows **and** Linux (future target: Raspberry Pi).
**Reuse what exists**: only improve the software when the hardware or a real need justifies it.

## Non-negotiable constraints
- **100% local and self-contained**: no paid service, no cloud AI. Internet only to update Scryfall data/prices (Wi-Fi is fine).
- **Embeddable**: everything must eventually run on a standalone machine (Raspberry Pi 5 as the brain, ESP32 for motors/sensors/LEDs/e-paper).
- **Cross-platform**: do not introduce Linux-only (e.g. `fcntl`) or Windows-only dependencies.
- **English only** in the repository: file contents, documentation, code comments, identifiers, file names and commit messages.

## Priorities
1. The Maker side (design, electronics, 3D printing) comes before the software.
2. Small iterations: get a working system first, then refine.
3. Stay incremental: don't build everything in V1.

## Current environment
- Windows PC (server / software) + iPhone (camera): the link works.
- Python 3.15 installed on the PC (`py` launcher).
- Current recognition: Tesseract OCR on Windows/Linux (Apple Vision on macOS, noticeably better); card data and prices from Scryfall. The offline database (~60 MB) is recommended to stay 100% local.
- Planned hardware: Raspberry Pi 5, ESP32, LEDs, e-paper display, 3D-printed parts (printer available through a friend).

## Current status
- Scanning from iPhone to PC works; recognition is partial.
- Main weakness: recognition. The set + collector number + name cross-check **already exists** in the code; it fails because Tesseract misreads the raw photo (see `docs/IDEAS.md`, OCR section).
- The original author published a 3D-printable scanning rig: https://makerworld.com/en/models/1152661 (possible starting point for stage 1).

## Code map (recognition) — `server.py`, "scanning" section (~lines 1480-1730)
- `detect_ocr_backend()`: Apple Vision (macOS), otherwise Tesseract.
- `_ocr_tesseract()`: Tesseract `--psm 3` on **the whole photo**, no cropping or preprocessing → normalized lines (bottom-left origin).
- `candidate_names()`: takes the topmost "mostly letters" lines of the image as the likely title.
- `parse_print_info()`: looks for the collector number (`NUM_RE`, e.g. `M 0026`) and set code (`SET_RE`, e.g. `TLE • EN`) in the 8 lowest lines.
- `identify_card()`: 1) set + number → exact printing, validated against the name (`names_agree`); 2) number + name; 3) fallback to fuzzy name match (no exact printing).
- Other files: `static/` (web UI), `deckbuilder.py`, `assistant.py` (optional), `test_games.py` (parsing tests).
- License: MIT (McDandle).

## Reference projects (sources of ideas, not bases)
Before copying any code: **check the license**. No LICENSE file → borrow the idea, not the code.
- `filipesibinel/scanner` (MIT): set + collector number + name cross-check, "needs review" queue, foil detection via the ★/• marker, "fixed area" mode. Linux-only and cloud AI → rejected as a base.
- `jlelectroterra1-jpg/card-scanner`: 100% local, RapidOCR, image-based recognition (MobileNetV2) when the name is unreadable, iPhone web version.
- `wmjg-alt/mtg_scanner`: OCR preprocessing (CLAHE + 2× upscaling).
- `MeIsGaggy/MTG-Card-Scanner-Sorter`: RapidOCR with Tesseract fallback, designed for Raspberry Pi.

## Where are the ideas?
- Detailed backlog: `docs/IDEAS.md`

## Working conventions with Claude Code
- Before changing code: read the repository README and explain the plan in a few lines.
- One change = one branch or one clear commit.
- **Commits follow [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0-beta.3/)**:
  ```
  <type>[optional scope]: <description>

  [optional body]

  [optional footer]
  ```
  - Types: `feat` (new feature), `fix` (bug fix), `docs`, `style` (formatting, no code change), `refactor`, `perf`, `test`, `build`, `ci`, `chore`.
  - Suggested scopes: `ocr`, `scan`, `ui`, `db`, `inventory`, `hardware`, `docs`.
  - Description in the imperative mood, lowercase, no trailing period, ~70 characters max (e.g. `feat(ocr): crop title bar before running tesseract`).
  - Breaking change: `!` after the type/scope (`feat(db)!: ...`) and/or a `BREAKING CHANGE: ...` footer.
  - One commit = one intent; if a commit mixes two types, split it.
- Do not refactor the original project without a reason tied to a need listed in `docs/IDEAS.md`.
- Every recognition improvement is measured on the test card set (success rate before/after).
- After each session: add a line to the decision log below.

## Decision log
- 2026-10-11: project scoped in a Claude Project; created `CLAUDE.md` + ideas backlog for continuity with Claude Code.
- 2026-10-12: 100% local / embeddable constraint adopted (no paid cloud AI).
- 2026-10-12: tested `filipesibinel/scanner` → does not start on Windows (`import fcntl`, Unix-only module) and has no UI screenshots. Rejected as a base.
- 2026-10-12: **decision: base = McDandle/local-mtg-scanner** (UI seen and liked, complete feature set, Windows + Linux). The other projects are a pool of ideas to make recognition more robust.
- 2026-10-12: fork `DonKadaj/local-mtg-scanner` cloned into `D:\Projets\11 - MTG Scanner\local-mtg-scanner` (remote `upstream` = McDandle). Reviewed the scanning code: the cross-check exists; the problem is OCR on the whole, unprocessed image.
- 2026-10-12: commit convention adopted: Conventional Commits.
- 2026-10-12: everything in the repository is written in English (contents, comments, file names); `docs/IDEES.md` renamed to `docs/IDEAS.md`.
