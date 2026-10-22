# VISUAL ACCEPTANCE RECORD

Only the owner can accept a video. Automated QC results are recorded here as evidence, never as approval.
MP4 files are not stored in git (`*.mp4` is ignored repo-wide); each entry lists where the file was delivered and its checksum.

| ID | Date | Gate | Owner status |
|---|---|---|---|
| V0-baseline-60s | 2026-10-18 (received) | — (prior engine output) | Not recorded. Used as the failure baseline. |
| V1-focus-13s | 2026-10-18 / 2026-10-21 | Style test before the mission | **Awaiting owner review.** Does not qualify as a Gate A candidate (see below). |
| P1-gate-a-preview | 2026-10-22 | Gate A preview (not a candidate) | Sent to owner. Explain-world shots only; story shots show ASSET PENDING; no voice; estimated timing. |
| A1-gate-a-v1 | 2026-10-22 | **Gate A candidate** | Delivered to owner's Telegram by the pipeline (run 39794737218). Superseded by A1-v2 (white flash fixed). |
| A1-gate-a-v2 | 2026-10-22 | **Gate A candidate** | **Awaiting owner verdict.** Sent in chat. |
| T1-tap-card-v1 | 2026-10-22 | Owner's own script (first full AI-directed film) | Delivered to owner's Telegram by the pipeline (run 39812806136). **My review: below the Gate A bar** (see below). v2 queued. |

---

## V0-baseline-60s

- **File:** owner upload `tiktok_60s_multi_engine.mp4`, 1080×1920, 30 fps, 60.0 s.
- **Production method:** Pillow 2D cards + Manim chart + espeak narration (`feature/tiktok-motion-engine`).
- **Measured defects:**
  - 5 cuts in 60 s (~12 s/shot; the reference averages ~1.9 s).
  - Static titles held 10–15 s.
  - Flat red/black boxes.
  - "Maps go dark" shown as an abstract network.
  - The 0–14 s segment is reused at 46–58 s.
  - Robotic espeak voice.
- **Owner feedback:** not recorded in this session. The master mission's failure list (slideshow editing, static compositions, robotic narration) matches it.

## V1-focus-13s ("Focus" premium motion style test)

- **Commits:** plates and source `8a4b45a`; delivery encode fix `1ef8daa`.
- **Render settings:**
  - Blender 5.2 Cycles CPU, 16 spp, OIDN denoise, motion blur, 1080×1920, 390 frames (~30 s/frame on 4 cores).
  - Remotion 4.0.300 composite, H.264 CRF 16, BT.709 limited range, AAC.
  - Synthesized music/SFX.
- **Production method:** procedural Blender 3D + Remotion kinetic type / UI dialog / cursor.
- **Output:** delivered to the owner as `focus_prototype_final.mp4` (12.99 MB, 13.056 s).
- **Inspector:** 9/9 technical checks pass (`tiktok_motion/premium/out/qa_report.json`). Evidence frames are in `tiktok_motion/premium/out/frames_bt709/`.
- **Defects found by my own inspection:**
  1. The ring reflection draws a scratch-like white streak across the sphere (~f225–235).
  2. Act 3 bokeh discs read as grey smudges.
  3. Sketch arcs cut through the hero sphere.
  4. ~2.5 s static hold in Act 1 and ~3.5 s at the end.
  5. **No voiceover.**
  6. **Single continuous shot**, so no cutting rhythm.
  7. No photoreal story world.
- **Why it isn't a Gate A candidate:** Gate A requires narration, multiple connected shots and narration-driven visuals. V1 has none of these.
- **Owner feedback:** pending.
- **Corrective direction:** if the owner likes the World 2 look, its components (kinetic type, dialog/cursor, Blender studio objects) carry into the Gate A capabilities. Its single-shot, no-VO structure is not repeated.

---

## Rendered outputs from other sessions, not inspected here

These exist per their own docs but were encrypted to the owner or sent privately by Telegram, so I couldn't view them:
- Semantic film (applicant → recruiter), PR #18
- God's Eye Atlantic route, 12 s (SHA256 `726c461d…`)
- Finance preview MP4
- `qa/*` premium-motion packs

The owner's verdicts on them, if any, should be added here.

---

## A1 — Gate A "The honest line" (v1 pipeline run, v2 local fix)

- **Produced by:** `studio-film.yml` run 39794737218 (order `studio/orders/gate_a.json`). Total 14 min, $0.
  - Tools: 2 min.
  - Kokoro voice: 26 s.
  - WanGP on Kaggle T4: 8 min (first still 102 s including model download, then 14 s each).
  - Render, master and inspect: 3 min.
  - Telegram delivery: 10 s.
- **Spec:** `studio/films/gate_a/spec.json`. 11 shots, 71 words, 30.7 s, 1080×1920, 30 fps. Two worlds:
  - Story world: 4 Z-Image Turbo stills with camera moves.
  - Explain world: phone/laptop UI flows, the city transfer, the quote card.
- **Inspector:** no technical defects. −14.3 LUFS integrated, −1.0 dBTP, H.264 yuv420p BT.709, AAC, no black or frozen stretches, 16 beats placed inside their shots.
- **My own visual review:**
  - Maya's identity is consistent across 3 separate generations (curly hair, grey hoodie, silver hoops, sage-green phone case). Daniel matches his description.
  - Every narrated action is on screen at its word: finds, taps Apply, types name / experience / honest line, Submit, Sent, departs, lands, inbox row arrives, opens, highlight, quote, call.
- **Defect found and fixed (v1 → v2):** a white phone screen flashed for about 0.3 s before the incoming call (the call screen faded in from transparent). v2 keeps the dark call background opaque. v2 SHA256 prefix `64f2d03babaa3628`.
- **Known limits:**
  - Story stills move only with camera (2.5D). Generated video is not used, because Wan 14B is too heavy for the free T4.
  - Laptop UI text is small on a phone screen even with the push-in.
  - There is no music bed yet (SFX only).
- **Owner verdict:** pending.

---

## T1 — "What Happens When You Tap Your Card" (owner script; Director = free LLM, no hand edits)

- **Produced by:** `studio-film.yml` run 39812806136 (order `studio/orders/tap_card.json`, attempt 5). Earlier attempts 3–4 failed in the Director (free LLM saturation, a stub answer outranking a real plan); fixed in `studio/director.py`.
  - Timings: Director 16 min (provider retries), voice 36 s, Kaggle stills 8 min, render 3.5 min. $0.
- **Inspector:** no technical defects. 37.9 s, 1080×1920, −14.3 LUFS, −2.0 dBTP, 11 beats placed. SHA256 prefix `123262e05678cb4a`.
- **My visual review (not acceptable as a premium result):**
  1. The Director used the phone-UI technique for the card chip and the terminal. Phones sat blank or locked for about 10 s (3–12 s, 30 s).
  2. `detail`/`confirm` screens with only a body line rendered almost empty (renderer drew no body).
  3. The data packet showed "Maya Rivera", a Gate A string hard-coded in the renderer. Other Gate A strings ("Jobs", "Apply · Northwind", inbox sidebar) were also hard-coded.
  4. Kinetic emphasis landed on filler words ("TO").
  5. "The bank checks three things" became a lone black dot (dots_subtract misused).
  - Good: both Lena stills (tap at the counter, coffee smile) are photoreal and consistent. Voice and timing are clean.
- **Fixes (v2):**
  - Renderer: all screen text comes from the spec; detail draws its body; the packet note is a parameter.
  - Validator: a screen with nothing to show is rejected.
  - Director: phone UI only for a person using an app; physical objects get still close-ups; filler emphasis is removed.
- **Owner verdict:** pending.
