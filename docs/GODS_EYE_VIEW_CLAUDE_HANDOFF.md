# God's Eye View integration handoff for Claude

**Continuation:** the original status below is historical. See
[GODS_EYE_CAPTURE_PIPELINE.md](GODS_EYE_CAPTURE_PIPELINE.md) for the implemented
upstream-viewer capture adapter, narrated Remotion test and current limits.

**Status: integration boundary implemented on an isolated GitHub branch, NOT an upstream Cesium capture pipeline or a verified final video.** Do not merge or deploy before testing and owner approval.

## Upstream (the real project)

- Canonical code: https://github.com/bilawalsidhu/gods-eye-view (MIT code, author Bilawal Sidhu).
- Engine: CesiumJS / Vite, Node 24.14.x or 26.x. It can boot keyless with Esri imagery / OSM fallback; not all imagery/data are licensed for commercial reuse.
- License and data-use requirements: upstream `LICENSE`, `DATA_SOURCES.md`, `SECURITY.md`, `CONTRIBUTING.md`.
- Commercial publishing: **never assume MIT on code covers satellite tiles, third-party layers, data, or recordings.** Do not ingest TeleGeography noncommercial data, billable Google/ion assets, unlicensed imagery, or live third-party feeds.
- The link is for auditing and producing a reviewed capture. The repo is NOT vendored into ours and no upstream code was copied.

## Implemented in this branch

1. `tiktok_motion/story_scene.py`: new `god_eye` kind accepts `geo_clip` and `geo_attribution`. A geographic narration cue, attribution, and a strictly constrained local `job/god_eye_<id>.mp4` path are mandatory. Decorative or URL-based clip paths fail closed.
2. `tiktok_motion/premium_job.py`: verifies local reviewed MP4 exists at planning time, before expensive Kokoro narration.
3. `tiktok_motion/premium/remotion/src/CinematicScene.tsx`: `GodEyeScene` renders the vetted local silent MP4 using Remotion `OffthreadVideo`; owner narration and captions remain controlled by the existing `Shot`. The upstream app is NOT embedded as a live iframe at render time.
4. `scripts/prepare_god_eye_clip.py`: user/Claude provides a separately reviewed local recording; the script probes, validates source duration, strips audio, converts to a Remotion-compatible 1080×690 H.264 preview, and returns scene metadata. It requires an explicit license-reviewed flag and attribution (a declaration, not proof of licensing).
5. `tests/test_god_eye_scene.py`: contract tests for accepted clip, path traversal, URL injection, unrelated narration, and attribution.

## Exact example scene

```json
{
  "narration": "Across the world, whale migrations follow ocean routes.",
  "kind": "god_eye",
  "on_screen": "Ocean migration routes",
  "camera": "orbit",
  "geo_clip": "job/god_eye_whales.mp4",
  "geo_attribution": "Imagery: [verified provider/license]; route: illustrative; recording: original"
}
```

Provide an owner-reviewed MP4 and check rights. In an authorized local checkout:

```bash
python -m scripts.prepare_god_eye_clip /path/to/reviewed-globe.mp4 \
  --clip-id whales \
  --attribution "Imagery: reviewed provider / license; route illustrative" \
  --commercial-license-reviewed
python -m pytest tests/test_god_eye_scene.py -v
```

## Tasks for Claude

1. Independently audit upstream `bilawalsidhu/gods-eye-view` and `DATA_SOURCES.md`; identify one safe, keyless, commercial-use-compatible basemap and test terrain on available FREE infrastructure. No assumptions about provider rights.
2. Implement deterministic Cesium camera storyboard `world → target region → route`, controlled by checked latitude/longitude and camera waypoints. Generate 5–8 seconds from *actual upstream* God's Eye View, not fabricated screenshots or SVG stand-ins. Reuse scene outputs for deterministic testing.
3. Audit/optimize CPU screenshot and ffmpeg capture performance with failure/resume behavior. Avoid Playwright iframe render loops during Remotion; record once, then ingest as MP4.
4. Verify integration with actual Remotion build/render and existing Alan7, LogicScript, finance and premium mode tests. No regression, no paid APIs, no deployment, no release.
5. Show real side-by-side review frame evidence and a genuinely meaningful geographic scene. Then request owner approval before merge/publish.
6. Most urgent quality requirement: fix **microdetail semantic editing** on the original system (actual items and actions, continuity, transitions). A prettier globe is not a substitute for story-directed scenes.

## What is NOT completed

- No actual upstream CesiumJS globe capture has been generated or reviewed.
- No end-to-end MP4 with the `god_eye` kind is verified.
- No automated mapping from ordinary narration to geographic coordinates/route data.
- No guarantee that footage is suitable for monetized YouTube, or that AI Director is universally cinematic.
- No cost, deployment, or publish actions were authorized or performed by this branch.

This deliberately avoids inventing capabilities and preserves the existing engine.
