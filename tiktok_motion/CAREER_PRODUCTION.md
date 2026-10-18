# YouTube AI Engine — Career short production proof

This change is an **actual repository entrypoint** for one registered topic.
It does not replace Alan7, LogicScript, the existing TikTok motion routes,
or the independent Blender/Remotion Focus prototype.

## Production command

From the repository root, in an environment with Python 3.11+, FFmpeg,
ffprobe, Pillow and NumPy:

```bash
python -m pip install Pillow numpy
python -m tiktok_motion.produce \
  --topic "5 types of job interviews" \
  --output outputs/career_60s.mp4 \
  --voice espeak
```

The `--voice espeak` option requires `espeak` or `espeak-ng` installed.
It is **robotic engineering narration**, not the desired natural premium voice.
Omit `--voice` to create an instrumental-only MP4 instead.

For a fast 4-second end-to-end render:
```bash
python -m tiktok_motion.produce \
  --topic job-interviews \
  --output outputs/career_preview.mp4 \
  --preview
```

Run focused tests:
```bash
python -m unittest -v tests.test_tiktok_career_production
```

The entrypoint calls the career motion rendering adapter, mixes original
locally synthesized soundtrack and optional offline voice, exports H.264/AAC,
probes the file, and writes a neighboring `*.engine_run.json` report. It
**does not upload, publish, approve, deploy, or call a paid API**.

## Proven scope vs. limitations

- Registered topic: `job-interviews` (also recognized as
  `5 types of job interviews`).
- Fixed, prewritten 60-second explanatory scenes. **No arbitrary-topic
  generation, AI research, open-ended script writing, or AI Director yet.**
- 720×1280 procedural design canvas, upscaled to 1080×1920, 24 fps.
  This is **not** native 1080p 3D Blender rendering.
- Motion: original 2D procedural illustrations, moving markers and wipes;
  original instrumental sound; optional espeak narration.
- The automated acceptance check verifies video/audio codec, resolution,
  duration, and presence of sound. It does not validate human voice quality,
  teaching quality, accessibility, monetization, originality against every
  source, or the owner's premium aesthetics.
- Unknown topics **fail explicitly**; no generic stock slideshow or false
  claims about successful AI generation.
- Every production report sets `requires_owner_approval=true`,
  `auto_publish=false` and `premium_quality_owner_approved=false`.

## Local proof

The 60-second end-to-end CLI was executed in a local test environment with
`--voice espeak`. It produced a 60.000-second 1080×1920 H.264/AAC MP4 and
a passed technical manifest; 4 focused tests passed. FFmpeg detected no
black stretches or frozen stretches longer than 2 seconds in the final test.
This is **local evidence**, not a GitHub Actions run or a live Telegram run.

Do not merge while the owner's independent Claude 3D work is underway.
