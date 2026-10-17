# Video 1 — production status (2026-10-15)

**Title:** Build a Free Expense Tracker That Catches Its Own Mistakes
**Lesson:** `content/expense-tracker-lesson/` (renderer: `spreadsheet`)
**Video 2 (preserved, unchanged content):** `content/expense-rule-lesson/` (renderer: `browser-app`)

## What exists

| File | Purpose |
|---|---|
| `content/expense-tracker-lesson/build_lesson.py` | Source of truth: narration, cued on-screen actions, 31 expected on-screen results |
| `content/expense-tracker-lesson/lesson.json`, `script.md` | Generated script (11 chapters, 1,064 words) |
| `content/expense-tracker-lesson/sources.md` | Claim audit and sources |
| `content/expense-tracker-lesson/LogicScript_Expense_Tracker.xlsx` + `build_template.py` | The free template (also what is recorded) |
| `brand/Video1_thumbnail_concept.jpg` | Thumbnail ("IT CAUGHT IT") |
| `production_pro/lesson_narration.py` | Shared narration stage (Piper + WhisperX; draft estimate for offline previews) |
| `production_pro/sheet_recorder.py` | Live LibreOffice recorder driven through UNO, captured with FFmpeg x11grab |
| `scripts/render_spreadsheet_lesson.py` | Spreadsheet renderer: narration → live recording with evidence → overlays + captions (single encode) → QC |
| `scripts/render_lesson.py` | Dispatcher by `lesson.json` "renderer" (both lessons) |
| `.github/workflows/lesson-render.yml` | Manual render job (not yet run) |

## Accuracy gate
Every important on-screen moment declares the value the live workbook must show (e.g. row 9 = `ERROR`,
"Amount is not a number."). The renderer reads those cells during the recording and aborts if any differ,
so the video can never show something the narration does not say. A draft render can never be packaged
for release.

## Offline evidence (this session, no Actions minutes, no paid APIs)
- Full DRAFT render, twice: 1920×1080, 24 fps, 7:46. 39 actions, maximum lateness 0.001 s.
  **31/31 live evidence checks passed.** 170 caption cues. The final Summary shows ALL CHECKS PASSED,
  with a total of 1,966.64 that matches a hand calculation.
- Template: 4,084 formulas, 0 errors. Examples, review and fully-fixed paths verified.
- Tests: **329 passed, 5 skipped** (`python -m pytest`). This includes a live LibreOffice test that reproduces the hook and the fix.
- The draft has **no voice** and uses estimated timing; it is watermarked "DRAFT PREVIEW".

## What the final MP4 still needs
1. **GitHub Actions minutes** (the allowance resets about 1 Nov). Run "Lesson render" with the lesson set to
   `content/expense-tracker-lesson` and draft unticked. Estimate: about 30–45 minutes (narration about 8–12,
   live recording about 8, single encode about 10, QC). Timeout is 60 minutes.
2. **Not verified until that run:** the UNO bridge with `setup-python` 3.12 (wiring is in the workflow),
   `fonts-inter`, and Piper/WhisperX timing (the draft used estimates; real cue times come from alignment).
   Action lateness above 0.9 s or any evidence mismatch fails the run instead of producing a wrong video.
3. **Owner review** of the final MP4, then `python -m scripts.lesson_release candidate ...` and `finalize`
   (see docs/YOUTUBE_UPLOAD.md). Upload privately first; owner publishes.
4. **Owner check** that the template imports correctly into Google Sheets and Excel before publication.
