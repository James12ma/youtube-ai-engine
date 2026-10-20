# Premium motion prototype — "Focus" (Priority 1 visual proof)

One original 13-second vertical piece (1080×1920, 30 fps, 390 frames) built to the owner's
reference (`clean.creator`-style editorial explainer). **It is a visual quality prototype for
owner approval, not yet a reusable template.** Nothing here is wired into the publishing path.

## What the reference does, and what this prototype borrows

| Reference trait | In this prototype |
|---|---|
| Paper-white studio, monochrome, one accent colour | Cycles-rendered white paper floor, black ceramic objects, red only on the UI "Remove" button |
| Real 3D objects with long, soft shadows (apple logo, globe, hourglass) | Glossy black hero sphere, 24 satellite spheres, orbit ring: 1 large soft key upper-left |
| Thin hand-drawn grid / crosshair lines under the object | Hairline 3D floor grid that fades out with distance |
| Black dots arranged around a big black circle | The same idea, as real 3D spheres that pop in, jitter, then get swept away |
| Tight bold sans + condensed italic serif emphasis word, grey secondary words | Inter Tight 800 + Playfair Display 900 italic (condensed 0.8×), muted grey words |
| UI dialog with a cursor clicking a destructive button | Frosted dark dialog "Remove “Distractions”?", cursor arcs in and clicks |
| Sweeping hairline arcs, underline arrows, blurred grey bokeh discs | SVG arcs + swoosh arrow drawn on, edge-only bokeh with parallax |

Story (13 s): *Most people think success means* **DOING MORE** → dialog removes 24 distractions →
*It means knowing* **WHAT TO CUT** → ring locks around the one thing left → *Less noise.* **MORE IMPACT**.

## Pipeline

```
timeline.json ──► blender/focus_scene.py (bpy 5.2, Cycles CPU) ──► 390 PNG plates
       │                                                                   │
       ├──► audio/make_score.py (numpy synth) ──► score.wav                │
       │                                                                   ▼
       └──► remotion/src (React) ── typography, UI, cursor, arcs, grain ──► MP4 ──► qa.py
```

* `timeline.json`: the single source of truth for beats and copy. Blender motion, Remotion
  typography and audio cues all read it, so they stay frame-locked.
* `blender/focus_scene.py`: builds the whole scene procedurally (materials, lights, camera, per-frame
  eased animation). `--save focus_scene.blend` writes an editable .blend.
* `remotion/`: composition layer. `npm run studio` opens Remotion Studio for live editing.
* `audio/make_score.py`: original synthesized sound design (pad, landing thud, dot pops,
  whooshes, click, chime). No samples, so there are no licensing concerns.
* `qa.py`: delivery checks + five evidence frames.

Motion Canvas and Manim were **not** used. Neither improves this look: Blender does the 3D and
Remotion does type and UI. The existing Manim adapter is untouched.

## Exact rendering commands

```bash
# one-time setup (free, local)
python3 -m venv ~/bpyenv && ~/bpyenv/bin/pip install bpy==5.2.2
cd tiktok_motion/premium/remotion && npm ci && cd ..

# full render: plates -> audio -> composite -> QA   (~3.5 h on 4 CPU cores, resumable)
BPY_PYTHON=~/bpyenv/bin/python ./render.sh
# fast timing preview: 25 % plates, 6 samples (~8 min)
PREVIEW=1 BPY_PYTHON=~/bpyenv/bin/python ./render.sh

# individual steps
~/bpyenv/bin/python blender/focus_scene.py --out remotion/public/plates --start 0 --end 389 --samples 16
~/bpyenv/bin/python blender/focus_scene.py --save focus_scene.blend          # editable Blender file
python3 audio/make_score.py --out remotion/public/audio/score.wav
cd remotion && npx remotion render src/index.ts PremiumPrototype ../out/focus_prototype.mp4 \
    --props='{"platesDir":"plates","withAudio":true}'
python3 qa.py out/focus_prototype.mp4
```

If Remotion's bundled Chrome download is blocked, pass any Chrome headless shell with
`CHROME=/path/to/headless_shell` (render.sh) or `--browser-executable` (npx).

## Licensing

* **Remotion** 4.0.300: the free license covers individuals, for-profit companies with **≤3 employees**,
  and non-profits, including commercial video output. Larger for-profit organisations need a
  Company License (remotion.pro). Checked against `node_modules/remotion/LICENSE.md`. Re-check if the team grows.
* **Blender / bpy** is GPL. Rendered images and videos are the owner's and are not covered by the GPL.
* **Fonts**: Inter Tight and Playfair Display, both SIL OFL 1.1 (via @fontsource), free for commercial video.
* Audio is synthesized in code. No third-party sound or music.

## Scope guard

Alan7, LogicScript, the existing TikTok engine, the Manim adapter and every publishing approval gate are unchanged.
No paid services, cloud render or GitHub Actions minutes were used. Nothing is published.
Priority 3 (turning this into reusable premium scene templates) waits for owner approval of the rendered MP4.
