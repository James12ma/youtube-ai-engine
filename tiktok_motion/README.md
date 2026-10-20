# TikTok Motion Engine

Multi-engine vertical explainer pipeline (1080×1920 @ 30 fps).

## Engines

| Engine | Status in this environment | License |
|--------|---------------------------|---------|
| **Manim Community** | **Working** — real adapter + Demo C | MIT |
| Motion Canvas | Adapter scaffold; **npm install blocked** (registry 502) | MIT |
| Remotion | Adapter scaffold; **npm install blocked** (registry 502). Free License OK for individuals / orgs ≤3 | Remotion Free / Company |
| Pillow | Always available (composition + demos A/B) | HPND |

Alan7 and LogicScript are **not modified**.

## Demos produced

- `demo_A_kinetic_news.mp4` — 15s kinetic typography news explainer (Pillow path; Remotion target style)
- `demo_B_map_network.mp4` — 15s animated map / network fade (Pillow path; Motion Canvas target style)
- `demo_C_manim_stats.mp4` — 15s statistical bar chart (**real Manim Community**)
- `tiktok_60s_multi_engine.mp4` — 60s concat of A+B+C+A

## Run

```bash
python -m unittest tests.test_tiktok_motion
python -m tiktok_motion.premium_demos          # A + B
manim -qh tiktok_motion/engines/manim_scenes/stats_demo.py InternetStatsExplainer
python -m tiktok_motion.render --generate-voice --output /tmp/out.mp4
```

## Blockers

1. **npm registry 502** — cannot install `@remotion/*` or `@motion-canvas/*` in this sandbox.
2. **Natural TTS** — `piper-tts` wheel fetch also failed (502). Narration remains espeak-ng engineering voice.
3. Word-level caption sync requires offline alignment (WhisperX/etc.) not installed.

Owner can install Node packages locally and the adapters will detect them via `available_engines()`.

No paid APIs, no publish, no merge without owner approval.
