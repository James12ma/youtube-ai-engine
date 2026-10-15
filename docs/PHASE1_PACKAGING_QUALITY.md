# Phase 1 — Packaging quality checks (2026-10-15)

Applies automatically to every video packaged with `python -m channel.cli package`.
Ported from `Jakeschincariol/youtube-agent-skill` (MIT) — see `THIRD_PARTY_NOTICES.md`.

Every finding is tagged with its source:

- **`[youtube]`** — a real platform limit. Always blocks.
- **`[project_policy]`** — a LogicScript quality preference. **Not a YouTube requirement.** Advisory by default; configurable.
- **`[style]`** — editorial hints. Never block.

## Always blocking (real YouTube limits)

| Check | Rule |
|---|---|
| Title | non-empty, ≤ 100 characters, no `<` or `>` (rejected by the YouTube Data API) |
| Supplied chapters | first at 00:00, ≥ 3, each ≥ 10 s **measured against the real MP4 duration** (YouTube silently ignores lists that break these). Configurable via `invalid_chapters_rule`: `block` (default) or `warn` (invalid chapters are then omitted from the description). |

## Project policy (warn by default)

| Setting | Default | Meaning |
|---|---|---|
| `title_desktop_chars` / `title_desktop_rule` | 60 / `warn` | desktop search usually truncates near 60 characters |
| `title_mobile_chars` | 40 | mobile preview shown in the report |
| `thumbnail_max_words` / `thumbnail_word_rule` | 3 / `warn` | legibility at feed size |
| `thumbnail_duplicate_rule` | `warn` | thumbnail text shares a content word with the title (plurals folded) |
| `thumbnail_text_required` | `warn` | thumbnail text unknown |
| `invalid_chapters_rule` | `block` | see above |

Each rule accepts `block`, `warn` or `off`. To enforce any of them, pass a JSON policy file:

```json
{"title_desktop_rule": "block", "thumbnail_duplicate_rule": "block"}
```

`--quality-policy policy.json` works on `thumbnail`, `quality-check` and `package`. Unknown keys are rejected. The policy that was applied is recorded in `quality_report.json`.

## Advisory only (never blocks)

- Hook score (specificity, address, stakes, curiosity, brevity → verdict, formula, suggestion). The upstream author reports it barely separates a creator's hits from misses; use it as a review prompt.
- Mobile preview, all-caps, vague words, no concrete anchor, filler at the front.
- Missing chapters, or chapters whose final length could not be checked because no video was given.

## Automatic for every video

- Drafts: `hook_advisory.json` is written next to `script.json` (a failure here never affects the draft).
- Renders: `render_report.json` includes a narration-timed `chapters` list (a short hook merges into the first section; the CTA folds into the last).
- Package: the description opens with two lines built from this video's hook, topic and section headings, then the validated chapter block; tags come from this video only; `<`/`>` are removed; the 5000-byte limit is enforced in bytes.
- `quality_report.json` is part of the release and covered by the approval digest. Editing or deleting it after approval makes `check` and `upload` fail.

## Commands

```bash
python -m channel.cli thumbnail --text "ONE CENT OFF" --title "<video title>" --out out/thumb.jpg
python -m channel.cli quality-check --draft <draft> --thumbnail out/thumb.jpg --chapters <render_report.json> --video <final.mp4>
python -m channel.cli package --draft <draft> --video <final.mp4> --thumbnail out/thumb.jpg \
  --chapters <render_report.json> --editorial-report <review.json> --out <release> [--title "<reviewed title>"] [--quality-policy policy.json]
```

The educational renderer's `qc_report.json` already contains a `chapters` timeline and can be passed to `--chapters`.

## Not yet verified

- The new `chapters` key in `channel/video.py` render reports has not been produced by a real Piper/WhisperX render yet (logic is unit-tested).
- No live LLM run has used the updated "≤ 60 chars" title instruction.
- The thumbnail text sidecar records what `make_thumbnail` drew. A thumbnail edited by hand afterwards is not re-read; pass `--thumbnail-text` in that case.
