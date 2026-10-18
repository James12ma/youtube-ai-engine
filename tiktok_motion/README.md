# TikTok Motion Engine — isolated vertical explainer

**Status:** End-to-end offline demo ready. Produces a 60-second 1080×1920 MP4 with scene-specific motion graphics, synchronized captions, and zero-cost English narration (espeak-ng engineering voice).

Demo topic: **What If the Internet Disappeared for 24 Hours?**

## Quick start (local, no paid services)

```bash
# Storyboard only
python -m tiktok_motion.storyboard

# Unit tests
python -m unittest tests.test_tiktok_motion

# Full render with engineering narration
python -m tiktok_motion.render --generate-voice --output /tmp/tiktok-demo-001.mp4
```

## Contract

- 1080×1920, 30 fps, exactly 60 seconds
- Six contiguous scenes with English on-screen text + narration
- Cream / black / red editorial palette
- `requires_owner_approval: true`, `auto_publish: false`
- Does **not** touch Alan7, LogicScript, or any publish path

## Limitations

- Narration uses espeak-ng (clear but robotic engineering voice). Natural neural voices (Piper etc.) can be swapped via `--voice` once locally available and approved.
- Captions are scene-level (not word-timed). Word-level alignment requires additional offline tools.
- Motion graphics are Pillow/vector 2D, not Remotion or After Effects.
- No network, no billing, no upload, no GitHub Actions required for the local demo.

## Next (owner-gated)

- Swap engineering voice for approved neural English
- Optional Remotion path after license/runtime review
- Owner listening + visual approval before any release
