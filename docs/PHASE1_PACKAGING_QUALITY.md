# Phase 1 — Packaging quality gates (2026-10-15)

Applies automatically to every video packaged with `python -m channel.cli package`.
Ported from `Jakeschincariol/youtube-agent-skill` (MIT) — see `THIRD_PARTY_NOTICES.md`.

## Blocking (packaging stops, exit code 2, nothing written)

| Check | Rule |
|---|---|
| Title length | ≤ 60 characters (desktop search cut); 100 is YouTube's hard limit |
| Thumbnail pairing | thumbnail text must share no content word with the title (plurals folded), ≤ 3 words |
| Thumbnail text known | taken from `--thumbnail-text` or the `<thumbnail>.text.json` sidecar written by `make_thumbnail` |
| Chapters (when supplied) | first at 00:00, ≥ 3 chapters, each ≥ 10 s, increasing, non-empty titles |

## Advisory (recorded in `quality_report.json`, never blocks)

- Hook score (specificity, address, stakes, curiosity, brevity → verdict + formula + suggestion).
  The upstream author reports it barely separates a creator's hits from misses; use it as a review prompt.
- Mobile preview (~40 chars), all-caps, vague words, no concrete anchor, filler at the front.
- Missing chapters.

## Automatic for every video

- Drafts: `hook_advisory.json` is written next to `script.json`.
- Renders: `render_report.json` now includes a narration-timed `chapters` list
  (short hook merged into the first section, CTA folded into the last).
- Package: description opens with two lines built from this video's hook, topic and
  section headings, then the validated chapter block; tags come from this video only.
- `quality_report.json` is included in the release and covered by the approval digest.

## Commands

```bash
python -m channel.cli thumbnail --text "ONE CENT OFF" --title "<video title>" --out out/thumb.jpg
python -m channel.cli quality-check --draft <draft> --thumbnail out/thumb.jpg --chapters <render_report.json> --video <final.mp4>
python -m channel.cli package --draft <draft> --video <final.mp4> --thumbnail out/thumb.jpg \
  --chapters <render_report.json> --editorial-report <review.json> --out <release> [--title "<reviewed title>"]
```

The educational renderer's `qc_report.json` already contains a `chapters` timeline and can be passed to `--chapters`.

## Not yet verified

- The new `chapters` key in `channel/video.py` render reports has not been produced by a real Piper/WhisperX render yet (unit-tested logic only).
- No live LLM run has used the updated "≤ 60 chars" title instruction.
