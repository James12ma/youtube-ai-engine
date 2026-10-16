# Live research → script → storyboard → verification: PASS (2026-10-16)

First fully successful live run of the automated content pipeline:
https://github.com/James12ma/youtube-ai-engine/actions/runs/38847225334

| Item | Result |
|---|---|
| Sources | 2 NIST publication pages retrieved (abstract/metadata pages, not full PDFs) |
| Model | `cohere/north-mini-code:free` — account and all prices verified zero |
| Generation requests | 18 of a 30-request cap; 0 paid calls |
| Script | **1,458 words, ≈ 9.7 min** (gate: 1,200–1,800 words, unchanged) |
| Storyboard | passed continuity and duration checks |
| Verification gate | 5/5 claims entailed, 0 contradictions, all spoken numbers traced to cited claims |
| Status | `awaiting_human_editorial_review` — nothing uploaded or published |

Draft files (script, storyboard, verification report, metadata draft) are in the
run's `source-script-dry-run-*` artifact (kept 3 days).

## What was fixed to get here (no threshold was lowered)
1. A too-short draft is expanded in the same revision, including the last one.
2. The expanded long draft is kept; sections or hook/CTA with spoken numbers not
   found in their cited claims are rewritten individually (exact offending words
   are named), instead of regenerating a short script.
3. `_validate_script` applies the final gate's spoken-number rule early.
4. Storyboard: 4096-token cap; scene timings derived from narration word share
   instead of model arithmetic; visual-type synonyms (e.g. "B-Roll") accepted.
5. Diagnostics: safe report/test summaries published as job annotations; schema
   and gate failures exported as field paths / categories only.

## Remaining before publication
- Owner editorial review of this draft (and of the rendered first tutorial).
- Secure rotation of the previously exposed Google OAuth credentials.
- Source quality: both sources are NIST abstract pages; fuller sources would
  make stronger lessons.

## Unreviewed preview render (2026-10-16)
https://github.com/James12ma/youtube-ai-engine/actions/runs/38886219188 — artifact `unreviewed-preview-38886219188` (kept 14 days)

| Item | Result |
|---|---|
| Title (draft) | Building a Cybersecurity Baseline for Small Business Automation |
| Duration | 625.46 s (10 min 25 s), 1920×1080 |
| Voice / alignment | Piper; WhisperX 1,458/1,458 words (100%) |
| Captions / chapters | 278 caption blocks; 8 chapters |
| Technical QC | PASS, no failures |
| Placeholder scenes | 8 (scenes 1, 4, 7, 10, 13, 16, 19, 22) — b-roll/recording/chart scenes with no real footage yet, shown as labelled cards |
| SHA256 | `9ae86dd1d5f385bd7c5de16f8ec50b56dc08dddc65c0e4858080ea915bb21e10` |

Status: **unreviewed preview, not publishable.** It was not watched or listened to by a
human in this session. Before release: owner review, real footage (or a decision to
replace those scenes with diagrams), then the normal reviewed render, package and approval.
