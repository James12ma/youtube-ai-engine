# Multi-engine motion integration — status

## Working

- **Manim Community v0.20.1 (MIT)** — real adapter, vertical 1080×1920 scene, Demo C MP4 verified.
- **Pillow composition path** — kinetic news (Demo A), map/network (Demo B), full 60s assembly.
- **visual_director** routes scene kinds; falls back to available engines.
- **Unit tests** green (8 tests).

## Blocked in this sandbox

- **Remotion** — Free License eligible for individuals / orgs ≤3. npm install fails with registry 502. Adapter scaffold only.
- **Motion Canvas** — MIT. Same npm 502 blocker. Adapter scaffold only.
- **piper-tts** — natural local voice; wheel download 502. Narration remains espeak-ng.

## Owner next steps (local machine)

```bash
# After npm registry is reachable:
npm install remotion @remotion/cli
npm install @motion-canvas/core @motion-canvas/2d @motion-canvas/ffmpeg
pip install piper-tts   # optional neural English
```

Adapters will report `available: true` once packages are present.

No paid services used. Alan7 / LogicScript untouched. PR stays draft.
