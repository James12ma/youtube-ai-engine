# TikTok Motion Engine — isolated foundation

**Status:** Phase 1 storyboard contract only. This is NOT yet a rendered MP4, an integrated production pipeline, or a publishing feature.

The first demo is a hypothetical 60-second English explainer: **What If the Internet Disappeared for 24 Hours?** It uses 1080x1920, 30 fps, six contiguous scenes, a cream/black/red editorial palette, and mandatory owner review.

Generate the storyboard locally without paid APIs or GitHub Actions:

```bash
python -m tiktok_motion.storyboard
python -m unittest tests.test_tiktok_motion
```

Next engineering work: inspect the existing narration and rendering adapters, add synchronized voice/captions and actual SVG motion graphics, export and decode-check an MP4, then run regression tests. Keep Alan7 and LogicScript untouched. Never auto-publish or use paid infrastructure.

Remotion may be considered after license eligibility and runtime compatibility checks; it is **not installed or required** by this foundation.
