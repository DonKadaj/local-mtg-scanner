# Ideas & backlog — MTG Scanning Station

> Living file: ideas are added as they come up. Each idea has a status:
> `💡 idea` · `🔍 to investigate` · `🔨 in progress` · `✅ done` · `❌ dropped`
>
> Reminder: everything must stay **100% local** (no cloud AI) and **cross-platform** (Windows + Linux/Raspberry Pi).

## 🧪 Before any improvement
- 🔍 **Test card set**: 15 to 20 cards, including the ones that fail today (white text on dark background, old cards, foils, borderless…). Record the baseline recognition rate, then measure it again after every change.

## 🧠 Software (to be done in Claude Code)

### OCR recognition
> **Diagnosis (from reading `server.py`)**: the title + collector number + set logic already exists (`identify_card`). But Tesseract runs with `--psm 3` on **the whole photo**, with no cropping or preprocessing. Consequences:
> - the title is guessed as "the topmost line of letters in the image" → if the title is misread (stylized font, colored background) or if background clutter sits above the card, the type line or rules text gets picked instead;
> - the bottom line (`M 0026`, `TLE • EN`) is small → often misread → falls back to a name-only search, with no exact printing.

- 🔍 **Step 1 — Straighten and crop**: detect the card outline (OpenCV, largest quadrilateral with 63×88 mm proportions), warp it flat, then cut two fixed regions: the title bar and the bottom-left corner.
- 🔍 **Step 2 — Per-region OCR**: Tesseract with `--psm 7` (single line) on each region, with preprocessing (grayscale, CLAHE, 2× upscaling, thresholding) — idea from `wmjg-alt/mtg_scanner`. Keep the current pipeline as a fallback if outline detection fails.
- 🔍 **Step 3 — OCR engine**: compare Tesseract and RapidOCR (local, ONNX) on the test set — idea from `MeIsGaggy` / `card-scanner`.
- 💡 Old cards (before ~2015) with no `set • language` line at the bottom: only the title and possibly the set symbol can identify the printing.
- 💡 Name matching more tolerant of OCR errors (accents, shortened names).
- 💡 **"Needs review" queue**: uncertain cards don't block scanning; they go into a queue to validate later (capture + suggestion + manual search).
- 💡 **Image-based recognition** as a last resort (unreadable name): image fingerprint compared with Scryfall images — idea from `card-scanner` (MobileNetV2). To be evaluated on Raspberry Pi.
- 💡 Ambiguous cases: show a grid of possible printings to pick from, instead of a flat failure.

### User interface
- 💡 The 2-3 small improvements spotted in the current UI (to be listed here).

## 🔧 Hardware / Maker

### Foil / non-foil detection
- 🔍 **Software first**: on recent cards (≈ 2020+), foils are marked with a **★** instead of a **•** next to the set code → read that corner with image processing, no AI. Cross-check with Scryfall (printings that only exist in foil or only in non-foil).
- 🔍 **Lighting** for cards without the marker: two shots with different lighting (angle, or LEDs on/off) and compare the reflections.
- 🔍 Tell **regular foil** from **surge foil** (different reflection patterns). Feasibility uncertain → to be tested experimentally.

### Embedded platform
- 💡 Brain: **Raspberry Pi 5** (OCR + recognition + web UI). An ESP32 is not enough for vision.
- 💡 ESP32 as a peripheral: feeder motor, sensors, status LEDs, e-paper; driven by the Pi (USB serial or Wi-Fi).
- 💡 "Fixed area" mode: the camera is fixed and the card always sits in the same place → reliable cropping without outline detection.

## 📌 Project stages (reminder)
1. Fixed scanning station: 3D-printed camera mount, card slot, even glare-free LED lighting (starting point: the author's MakerWorld rig, model 1152661).
2. Automate card feeding: hopper, one-card-at-a-time mechanism, sensors, motor, ESP32.
3. Status LEDs, e-paper display, physical controls.

## 🗒️ Misc
- (loose ideas go here)
