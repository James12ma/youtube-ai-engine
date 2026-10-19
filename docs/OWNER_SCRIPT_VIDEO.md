# My Script -> Video: Owner-controlled storyboarding (isolated branch)

The owner supplies every word of the narration. AI must never rewrite, add, or
replace spoken lines unless the owner requests a script change. This feature
is being developed inside the EXISTING YouTube AI Engine.

## Phone-friendly mode: just text

Save text as `my_video.txt`; put each narration scene in a separate paragraph.
An optional first line `# Title` sets the title. This uses **generic kinetic
scenes** and requires owner visual review.

## Exact scene mode: JSON

See `examples/owner_script_job_interview.json`: each scene specifies:

- `narration`: exact words spoken (immutable).
- `kind`: kinetic, cards, chart, process, ui, or timeline.
- `on_screen`: visible headline.
- `items`: card/chart/process/timeline labels.
- `visual_notes`: optional additional direction preserved verbatim and flagged
  for human review; it is NOT magically implemented by the template.
- `duration_seconds`: planned length (not guaranteed speech fit).

Either format can use multiple scenes. JSON also selects `en` or `es`.

## Create a storyboard now (no cloud costs)

```bash
python -m tiktok_motion.owner_script_input \
  --script examples/owner_script_job_interview.json \
  --plan-out outputs/my_storyboard.json
python -m unittest -v tests.test_owner_script_input
```

The output contains exact narration, a SHA256 of the owner's input,
scene timing, supported kinds, warnings for unimplemented visual directions,
and mandatory review flags.

## What is and is not implemented

**Implemented in GitHub:** script ingestion (text or structured JSON), reliable
storyboard output, a deterministic preview contract, tests and owner approval
guard. It does NOT yet take arbitrary owner scripts end-to-end to a natural-voice
premium MP4. The earlier career proof renderer still contains fixed content.

**Local experiment:** an animated 4-second visual preview was generated from a
sample owner script; source and six passing local tests are supplied separately
for integration/review. No Chatterbox audio has been generated for that demo.

**Next integration requirements:** connect this storyboard to reusable premium
motion templates; generate approved English/Spanish Chatterbox lines; measure
every voice segment; synchronize/correct timeline; visual QA; full 1-2 min MP4
with owner approval only. No publishing or paid render without owner consent.

Original Alan7 and LogicScript production paths remain untouched. Do not merge
before acceptance.
