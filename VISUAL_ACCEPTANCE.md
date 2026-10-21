# VISUAL ACCEPTANCE RECORD

Only the owner can accept a video. Automated QC results are recorded here as evidence, never as approval.
MP4 files are not stored in git (`*.mp4` is ignored repo-wide); each entry lists where the file was delivered and its checksum.

| ID | Date | Gate | Owner status |
|---|---|---|---|
| V0-baseline-60s | 2026-10-18 (received) | — (prior engine output) | Not recorded. Used as the failure baseline. |
| V1-focus-13s | 2026-10-18 / 2026-10-21 | Style test before the mission | **Awaiting owner review.** Does not qualify as a Gate A candidate (see below). |

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
