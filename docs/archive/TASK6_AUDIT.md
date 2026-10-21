# Task 6 — Video Production Prototype: Local Audit

Audited in a local Linux environment with FFmpeg 7.1.5, Python 3.13.5. No live LLM or Edge TTS network requests were made. No uploads and no paid API calls.

## Findings in DeepSeek's proposed code (not executed as originally supplied)

1. **Blocker: malformed FFmpeg `loudnorm` option separators**. It joins filter arguments with commas, which FFmpeg interprets as separate filter commands. A real local FFmpeg invocation confirmed the failure. Correct usage joins options with colons (`:`).
2. **Missing hook + CTA**. The original renderer synthesizes only `script.sections`, discarding the introduction and closing CTA from output audio.
3. **Fabricated charts**. The original `assets.py` uses SHA-256-derived random bar heights without source data. This creates misleading numbers. The corrected proof-of-concept refuses unsupported charts.
4. **No genuine screen recording**. Original `screen_recording` renders a conceptual diagram. The corrected module refuses such a scene without a genuine visual source (in this MVP, the render stage rejects unsupported genuine footage scenes; Task 7 must integrate actual captures).
5. **Synchronization and missing content**. The original video timing makes scenes at least min_scene_s, may lengthen video against the audio, and final `-shortest` can clip scenes. The corrected demo derives each scene's duration from actual rendered narration and checks output vs audio length.
6. **Quality gate wasn't enforced**. The original verification *measures* audio levels but does not reject loudness outside acceptable ranges; required caption burning degrades into an optional warning. Corrected prototype validates both.
7. **Caption lines**. Original grouping checks total characters, not per-line width or actual line counts. The corrected prototype writes explicit ASS `\\N` wraps.
8. **TTS caveat**. `FakeTTSBackend` generates an electronic tone, not speech. Edge TTS is an unofficial online dependency, not a guaranteed cost-free/commercial-licensing solution. This environment used installed `espeak` for real but robotic speech. Approximate word timings require later alignment verification.
9. **Compute**. 4× enlarged images at 1080p can exceed the memory budget of free runners. The corrected pipeline defaults to 1× and limits upscaling.
10. **Preflight**. The corrected renderer requires explicit `approved=True` and still never publishes; this is an engineering protection, not a cryptographic signed approval system.

## Verified tests and output

- `python -m compileall -q production tests`: PASS.
- Entire Python suite for Tasks 1–6: **134 passed, 3 skipped**. The 3 skipped tests are live external API smoke tests.
- Local real 1080p prototype generated at `/mnt/data/youtube_ai_task6_1080p_engineering_demo.mp4` using `EspeakOfflineBackend`, **not** Edge TTS:
  - 1920 × 1080, 24 fps, H.264 video/AAC audio, 13.458 seconds
  - EBU R128 loudness reading −16.67 LUFS, true peak −1.30 dBTP
  - 3 scenes, 4 caption groups
  - A still frame was visually inspected; captions render correctly
  - `ready_for_publication` remains FALSE
- A separate low-resolution video with `FakeTTSBackend` was rendered and validated in unit tests; it is not human narration.

## Remaining blockers to YouTube publication

1. Real software capture and truthful screen demos that can be audited scene by scene.
2. Credible voice rights/licensing and natural narration with accurate word alignment.
3. Better motion design and asset diversity; the prototype has stylized static cards and slow zoom only.
4. Editorial signoff for authentic sources, originality, usefulness and claims.
5. Visual/perceptual QA of final output and caption timing by an independent reviewer.
6. Production deployment, real provider API availability and reliable scheduling have not been validated.

The current clip should be treated as a **proof that the local render stack can generate an MP4**, not as an ad, monetizable YouTube video, or finished autonomous business.
