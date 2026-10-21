# Gate 1 — Reference video analysis

Status: **complete for the one reference available.** Evidence date: 2026-10-21.

## Inputs actually analysed

| Input | Format | Role |
|---|---|---|
| `68676789-….mp4` (owner upload) | 576×1024, 30 fps, 35.04 s, H.264 + AAC 44.1 kHz stereo | **The only true quality reference** (`@clean.creator`, Spanish, about Apple in 1997) |
| `77c45b28-tiktok_60s_multi_engine.mp4` (owner upload) | 1080×1920, 30 fps, 60.0 s | Earlier engine output, used as the **failure baseline** |
| `focus_prototype_bt709.mp4` (this branch) | 1080×1920, 30 fps, 13.06 s | Earlier style test (see VISUAL_ACCEPTANCE.md) |

**Limitations, stated up front:**
- The mission refers to "reference videos" (plural). Only **one** reference was supplied to this session.
- **No speech transcript could be produced.** Hugging Face, OpenAI and Vosk model hosts are blocked by this environment's network policy. Narration content below comes from the burned-in on-screen words, which follow the voice word by word.
- Reference frames are **not committed**: the repository is public and the frames contain third-party marks and a real person's likeness. The contact sheets (3 fps, timestamped) were delivered to the owner privately.

## Measured facts (verified with ffmpeg / numpy)

- **Hard cuts** (ffmpeg `scdet`, threshold 8): 0.30, 0.53, 0.80, 1.03, 1.60, 3.43, 4.87, 7.57, 9.27, 11.57, 13.03, 15.77, 18.27, 24.10, 31.00 s. That is 15–17 visual changes in 31 s of content, a **mean shot length of ~1.9 s**. Within each shot the on-screen text changes every **0.3–0.5 s**.
- **Voice:** voice-band syllabic modulation (3–8 Hz) stays at 0.33–0.43 from 0 to 30 s and drops to 0.15 on the end card. This strongly indicates continuous voiceover over music. Not verified by transcript.
- **Music bed:** steady sub-200 Hz energy throughout.
- **Audio level:** RMS ≈ −18.3 dBFS, peak **+1.98 dBFS**, so the reference itself clips slightly. Do not copy that.
- **End card:** 31.0–35.0 s is a branded TikTok outro. Silence starts at 32.1 s.

## Time-coded scene analysis

Narration is reconstructed from the on-screen words. The English gloss is mine.

| Time (s) | Narration (on screen) | What the picture does | Technique (hypothesis unless noted) |
|---|---|---|---|
| 0.0–1.6 | "en 1997" ("in 1997") | Four rapid dark, cinematic establishing stills: rainy city street, payphone at dusk, cluttered 90s office, messy room. Huge frosted "1997" stays locked centre while the backgrounds cut underneath. | AI-generated photoreal stills (giveaways: garbled signage, perfect period clutter), slow push-ins, glassy/blurred text treatment. **Cut every ~0.3 s while the word holds**, which says "an era" through montage. |
| 1.6–3.4 | "Apple estaba al borde" ("Apple was on the edge") | Hard cut to a white paper world. A glossy black 3D logo badge inside a dashed ring, with petal-like shadows in the corners. Words stack in as they're spoken; at "al borde" the badge **cracks**. | 3D object render or cut-out on white with a soft shadow, plus 2D type. **The visual acts out the meaning:** "on the edge" becomes a cracking emblem. |
| 3.4–4.9 | "la empresa perdía MILLONES" ("the company was losing MILLIONS") | Dark boardroom: whiteboard "1997 Q1 NET LOSS $708 Million" with a falling red bar chart, newspaper "Apple Posts $708 Million Loss" on a cluttered desk. Slow push. "MILLONES" in big frosted italic. | AI still with a chart and headline painted into the scene. **The data lives inside the world**, not in a separate chart graphic. |
| 4.9–6.2 | "tenía Demasiados PRODUCTOS" ("had too many PRODUCTS") | Warehouse overflowing with boxed 90s computers. | AI still. "Too many" is shown as visual abundance. |
| 6.2–7.6 | "y nadie sabía qué hacer" ("and nobody knew what to do") | Man slumped at a desk at night, head in hand, storm outside, company building through the window. Words stack vertically. | AI still with slight motion. **Emotion is carried by a person's body language.** |
| 7.6–9.3 | "entonces volvió… Steve Jobs, Fundador de Apple" ("then … returned, Steve Jobs, founder of Apple") | Cut-out portrait on white, holding a red apple. Name label with a hand-drawn connector line; "entonces volvió" annotation. | Photo cut-out with drop shadow, editorial annotation style. Real person: **rights-sensitive**. |
| 9.3–11.6 | "y tomó una decisión que parecía una locura" ("and made a decision that seemed crazy") | B/W archival-look shot, arms crossed, slow push. One word at a time, centred; "locura" switches to italic serif. | Archival footage or AI-animated still. **One-word-at-a-time pacing builds tension.** |
| 11.6–13.0 | *(implied: he deleted products)* | UI metaphor: a product catalogue (eMate, MessagePad, Mac, Macintosh) with a dark dialog **Eliminar "Productos"** (Cancel / Delete). The cursor clicks Delete, the cards turn **red**, then vanish. | Motion-graphics UI mock-up with cursor animation. **The abstract decision becomes a concrete action** with a cause (click) and an effect (cards flagged and removed). |
| 13.0–15.7 | "Apple dejó de VENDERLE a todo el …" ("Apple stopped SELLING to every…") | White grid; words appear at their spoken moments; grey 3D globes slide in from the corners; a hand-drawn arc arrow under "a todo el". | Kinetic type + 3D globe render + drawn-on stroke. |
| 15.7–18.3 | "Empezó a ENFOCARSE" ("It started to FOCUS") | Taped polaroids pile up on a grid, each a dark AI photo of a small team around a few computers, labelled "PowerBook (1997)", "Power Macintosh (1997)", "Desktop Mac (1998)". | AI stills framed as polaroid assets. **"Focus" becomes a curated few products.** |
| 18.3–19.2 | "¿El Resultado?" ("The result?") | White; the question builds, then a motion-blurred whip zoom on "Resultado". | Type-driven transition. |
| 19.2–20.3 | "Años después…" ("Years later…") | 3D brass hourglass on a faded clock face, flying through the frame. | 3D asset. **Time passing is shown as an object.** |
| 20.3–24.1 | "esa misma EMPRESA se convertiría en una de las más valiosas del mundo" ("that same COMPANY would become one of the most valuable in the world") | Floating 3D matte-grey logo with soft shadow and drifting grey bokeh dots; long sentence flows word by word in a mixed grey/black, mixed-size line. A blur transition between beats. | 3D object + 2D particles + kinetic type. |
| 24.1–26.3 | "Todo empezó cuando ENTENDIERON algo…" ("It all began when they UNDERSTOOD something…") | Monochrome 3D brain on a grid, crossed by two sweeping hairline arcs. | 3D asset + 2D strokes. **"Understanding" is shown as a brain.** |
| 26.3–31.0 | "No significa HACER MÁS. Significa saber QUÉ ELIMINAR." ("It doesn't mean DOING MORE. It means knowing WHAT TO REMOVE.") | Black disc on a grid; ~40 dots pop in around it ("doing more"). On "QUÉ ELIMINAR" the dots **fade to grey and disappear**, leaving the disc. | Pure 2D vector motion. **The thesis is shown by subtraction.** |
| 31.0–35.0 | — | Branded TikTok outro (glitch bars, search field "@clean.creator"). | Platform template. |

## Cinematic grammar

- **Two alternating worlds.** World 1 is a dark, photoreal "story" world for the problem (the past, emotion). World 2 is a bright, clean white "explanation" world for concepts and the solution. Cutting from dark to white marks the turn from problem to insight. This is a deliberate narrative structure.
- **Camera:** mostly slow push-ins and drift (2.5D Ken Burns on stills), plus a few whip/blur zooms at transitions. There's no complex 3D camera choreography; the energy comes from cutting and type.
- **Lighting:** World 1 uses warm practicals and low key. World 2 uses one soft key from the upper left, long soft shadows toward the lower right, and paper white.
- **Composition:** the subject sits centre to lower-middle and the text block sits in the upper third. Very little dead space, because an object, type or texture always occupies the frame.
- **Continuity devices:** the grid recurs (13 s, 15 s, 24 s, 26 s), objects carry the same soft-shadow look, and text stays in the same zone. This makes an assortment of assets feel like one world.

## Motion-design grammar

- **Kinetic typography is the spine.** Every narrated word appears on its spoken syllable. Small bold grotesk carries the running words, grey for secondary words. A condensed italic serif carries the emphasis word, often 2–3× size. Glass/frosted or motion-blur letter reveals are used throughout.
- **Micro-interactions:** the cursor click causes the card colour change, which causes removal; the crack on "al borde"; dots popping in on "hacer más" and leaving on "eliminar"; the arc arrow drawing under "a todo el".
- **Curves:** fast ease-out (settle) entries, blur-in on words, and whip-blur transitions between sections.

## Editing grammar

- Mean shot length ≈ 1.9 s. Montage cuts (0.3 s) under a held word. A new text beat every 0.3–0.5 s, so attention is never idle.
- **Narration → picture binding is per phrase and often per word.** Each key noun or verb gets a visible counterpart: losing millions → loss chart; too many products → warehouse; deciding → dialog + click; focus → three polaroids; years later → hourglass; understood → brain; remove → dots disappear.
- Music bed under continuous VO. The end card is silent apart from a jingle.

## What the failure baseline gets wrong, by comparison (measured)

| Property | Reference | Earlier engine 60 s output |
|---|---|---|
| Visual changes | ~17 cuts in 31 s (1.9 s/shot) | **5 cuts in 60 s** (~12 s/shot) |
| Text cadence | word-synced, every 0.3–0.5 s | static titles held 10–15 s |
| Imagery | photoreal story stills + 3D objects | flat red/black 2D boxes, network blobs |
| Narration ↔ visual | each key phrase acted out | generic ("Maps go dark" = abstract network) |
| Repetition | none | 0–14 s segment reused at 46–58 s |
| Depth/lighting | soft shadows, 3D, depth of field | none |

The earlier **Focus** prototype matches World 2 (paper white, 3D objects, kinetic serif type, dialog + cursor). It still falls short of the reference: it has **no voiceover**, it's **one continuous shot** (no cutting rhythm), it has **no World 1** (no photoreal story imagery), and it uses ~3 text beats where the reference has ~30.

## Capabilities required to reproduce these techniques

| # | Capability | Needed for | $0 feasibility (hypothesis until proven) |
|---|---|---|---|
| C1 | Natural voiceover with **word timestamps** | Everything (type sync, cut timing) | **Feasible.** Kokoro-82M (Apache-2.0) is already used on other branches with native word timings. Spanish quality needs owner listening. |
| C2 | **Word-synced kinetic typography** engine | Spine of the style | **Feasible.** Remotion; the Focus `Kinetic.tsx` already does the visual style. |
| C3 | **Photoreal story stills** on demand (World 1) | Era, emotion, places, people | **Hardest piece.** Needs a free image model (e.g. FLUX.1-schnell / SDXL on the Kaggle free GPU). Not proven in this repo. Without it, World 1 is impossible and the result degrades to motion graphics only. |
| C4 | 2.5D camera on stills (push/parallax, depth) | World 1 motion | Feasible. Remotion transforms; depth parallax needs a depth model (runner/Kaggle). |
| C5 | Clean 3D object library on white, soft shadows | World 2 | **Proven:** the Blender Cycles path (Focus). Slow on CPU (~30 s/frame at 1080×1920); a GPU or pre-rendered asset reuse is needed for volume. |
| C6 | UI metaphor kit (dialogs, cards, cursor, state changes) | Decisions and actions | **Proven** in Focus (Dialog + Cursor). Needs a general component set. |
| C7 | 2D vector motion (dots, arcs, arrows, grids) | Abstract ideas | Feasible in Remotion. |
| C8 | Shot-level director: phrase → visual counterpart → technique | Narration ↔ picture binding | **Missing in the repo** (see the Gate 2 audit). This is the core build. |
| C9 | Editor: montage cuts, whip/blur transitions, music + SFX mix | Rhythm | Feasible (Remotion + ffmpeg). |
| C10 | Licensed archival/real footage | Real people and events | Rights-limited. The repo has Commons/Pixabay/NOAA discovery with licence gates. **Real-person likeness (e.g. Jobs) should be avoided or be properly licensed.** |

## Production-method assessment (hypotheses, labelled)

- Most likely made in CapCut or After Effects from templates. Dark scenes are AI-generated stills (strong evidence: garbled text, the "Steave" misspelling, perfect period clutter). The 3D objects are probably stock 3D/PNG renders with drop shadows. Kinetic type is template-driven. The dots/grid scene is simple vector animation.
- **Not** generative video and **not** bespoke 3D animation. The premium feel comes from **asset quality + word-level sync + cutting rhythm + a consistent two-world art direction**, not from expensive rendering. This matters for the $0 budget: the hard part is C3 (stills) and C8 (direction), not GPU-heavy video generation.
