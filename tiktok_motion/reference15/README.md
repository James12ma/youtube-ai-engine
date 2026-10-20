# Motion Reference 15 — original test from YouTube AI Engine

**Status:** isolated visual direction reference, subject `How AI chooses the next word`. All seven user-submitted MP4s are **visual references only**, not included/reproduced in the output; no copied logos, footage, or audio.

## Quality direction extracted from user references

- Dark editorial UI, orange accents, precise grid and typography; consistent palette across scenes.
- Visual explanation with animated token chips, bar-chart scoring, cursor and progress graph rather than stock footage or slide transitions.
- Every scene moves internally; enter/exit transitions overlap; original synchronized synthetic score and sound cues.
- 15 s, 1080x1920 H.264/AAC 30 fps, safe margins for vertical video.
- Probabilities are intentionally **illustrative**, not measured from a language model.

## What this proof *does* / *doesn't* prove

- Generated programmatically by a new module inside the existing repository with Pillow+NumPy+FFmpeg. Works offline and does not consume GitHub Actions minutes or paid APIs.
- Uses a native 720x1280 procedural canvas for performance, Lanczos down/up to 1080x1920 delivery. It is **not** Blender-quality native 3D, nor yet Remotion/Manim orchestration. Technical output can pass while human visual taste still fails.
- No natural human voice: original synthetic sound only, to avoid substituting robotic eSpeak for premium narration.
- **Fixed pilot script only**: not arbitrary topic generation, not a complete AI Director, and not publication-ready without owner approval.

## Run locally

From repository root (Python 3.11+, Pillow, NumPy, FFmpeg/ffprobe installed):

```bash
python -m unittest -v tests.test_premium_motion_reference15
python -m tiktok_motion.reference15.produce --preview --output /tmp/motion15_preview.mp4
python -m tiktok_motion.reference15.produce --output /tmp/motion15.mp4
```

The JSON technical report next to each MP4 has `auto_publish=false`, `requires_owner_approval=true`. No publishing integration. No existing LogicScript/Alan7/Claude branch files modified. This should become a scene-template approach only **after** the owner approves the preview aesthetics.
