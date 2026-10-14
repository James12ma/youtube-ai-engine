# Task 7 audit — 2026-10-13/14 (local engineering proof)

## Actual results
- Full repo: `142 passed, 3 skipped` in pytest on this machine, with no external LLM provider calls.
- Real Chromium was driven using Playwright. Due to this environment's policy blocking loopback and `file://` navigation, the functional original HTML/CSS/JS was injected in-browser with `page.set_content`; genuine event handling and DOM updates were recorded.
- Video produced: `youtube_ai_task7_real_browser_demo_1080p.mp4` 1920x1080, 24fps, H.264/AAC, 33.98s. `ffprobe` and EBU R128 QC passed. Measured -16.48 LUFS and -1.34 dBTP; counted black portion 0, silence ~9.7%; ASS coverage of audio timeline ~100% **does not prove word sync**, because it uses approximate timing.
- Voice in demo is espeak, NOT natural Piper. No Piper model was downloaded or deployed. Neural voice quality remains unverified.
- No publishing or uploads occurred. No paid API requested. Test data is purely locally generated and rules executed by our original UI.

## Issues in DeepSeek's original proposal
1. Piper `voice.synthesize()` chunks cannot be written directly to an arbitrary empty WAV header; use documented `synthesize_wav` and confirm ONNX+JSON voice files.
2. Sidecar phoneme timing metadata was assumed but not established; character-based interpolation was falsely described as genuine phoneme alignment.
3. `EditPlan` start/end, zoom, highlights were not actually used, and still PNGs did not have loop/duration handling.
4. User-supplied `EvidencePoint` URL/snippet was not cross-validated with an accepted Task 5 claim or cached source text; additionally extracted numerical value could be fabricated.
5. `caption_coverage=1.0` was hardcoded rather than calculating actual occupied subtitle intervals.
6. Evaluating FPS via Python `eval` on ffprobe output was unsafe; rational ratios should be parsed instead.
7. Absence of valid lossless reference prevents meaningful VMAF, so report it as not measured rather than claiming quality.
8. Piper library's software license is not a blanket guarantee of commercial licensing for all voice models; check the specific model card.
9. Recorder is a real original demo, not a popular third-party SaaS workflow. Its commercial storytelling value remains limited.

## Remaining work before commercial production
- Install/download an appropriate, commercial-use-approved local neural voice with model license and test it; use real forced alignment of generated speech to subtitles.
- Refine editorial experience with cuts and focus anchored on actions, legible captions, a meaningful hook, and genuinely useful SaaS workflows.
- Evaluate the rendered 1080p video with a human; no perceptual/technical threshold alone proves watchability.
- Do an opt-in online smoke test of upstream free model providers; no blanket guarantee of $0 inference or YouTube monetization.
- Build only verified analytics and uploader/publisher later, with explicit approval and safety checks.
