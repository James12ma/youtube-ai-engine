# Concat feasibility test: headless MCP editor on a free runner

Date: 2026-10-23. Branch: `experiment/concat-headless` (based on `feature/gods-eye-view-integration` @ `bfb8957`).
Spend: $0. Nothing was merged, deployed or published. Concat runs as a separate program over stdio, so no Concat code is in this repository.

## Verdict

**Do not integrate Concat into the production pipeline now.**
- Concat runs reliably headless on a standard free GitHub runner, using the software GPU (llvmpipe).
- It produced a correct 15 s film with transitions, animated titles and synchronised audio.
- On the same edit, Concat matched the existing engine on transitions and made better-looking titles out of the box.
- Concat was 2.2× slower and used 2.5× more memory. It needs a separate loudness master.
- One title-keyframe bug turned up, and needs a workaround.

None of these is a measurable advantage that justifies a new dependency (AGPL-3.0, 370 MB installed). The prototype stays on this branch as an optional tool.

## What ran (all on `ubuntu-24.04`, 4 vCPU AMD EPYC 7763, 16 GB, no GPU)

| Run | Purpose | Result |
|---|---|---|
| 39889048512 | Install + MCP probe | Concat 0.2.8 `.deb` installed in 40 s. `concat --mcp headless` started (`mcp.mode=headless`). 42 tools, 127 effects. Peak 76 MB. Vulkan device: llvmpipe (LLVM 20.1.2). |
| 39890127835 | First render | My driver bug (read `clips` instead of `timeline.clips`). Fixed in `8a36f3c`. |
| 39890434357 | Render + compare | Concat export OK (450 frames). Compare script drifted by a frame on one file; fixed in `c8d8b94`. |
| 39891782805 | Render + compare + title probe | Found the title-keyframe bug (below). |
| **39892495208** | **Final render + compare** | **Both outputs verified. Numbers below come from this run.** |

Evidence for each run (MP4s, frames, logs, JSON) is on branch `concat-probe/<run id>`.

## Same input, two engines

`timeline.json`:
- 5 clips at 1080×1920, 30 fps, 15.0 s
- transitions into clips 2–5: fade, slide, wipe, fade (0.4 s each)
- 5 animated titles: rise, scale 86→100 % and fade in, then fade out
- 5 narration lines (espeak-ng) placed 0.2 s into their clips, plus a −18 dB music bed

`make_media.py` generates all media with seeded ffmpeg generators, so the output is byte-identical on every machine.

- **Concat:** `concat_path.py`. `concat --mcp headless`, `CONCAT_GPU=software`, 86 MCP calls, H.264 CRF 18.
- **Existing engine:** `baseline_path.py`. `production_pro.editing.compose_scenes` (ffmpeg `xfade`), an adelay/amix/loudnorm mix, and animated ASS titles through `burn_captions`.

| Measure (run 39892495208) | Concat 0.2.8 | Existing engine |
|---|---|---|
| Duration / frames | 15.000 s / 450 | 15.000 s / 450 |
| Format | 1080×1920, 30 fps, H.264 yuv420p, AAC 48 kHz stereo | same |
| Colour tags | BT.709, limited range (tagged) | untagged |
| Wall time (edit + render) | 41.6 s (3.8 s edit + 37.6 s export). Earlier runs: 57.4 / 57.7 s | 18.8 s. Earlier runs: 27.2 / 27.1 s |
| Peak memory | 2,230 MB | 889 MB |
| CPU | 322 % | 301 % |
| File size / bitrate | 14.9 MB / 7.8 Mb/s (CRF 18) | 8.9 MB / 4.6 Mb/s (CRF 21) |
| Loudness | −22.0 LUFS, −5.9 dBTP (not normalised) | −15.1 LUFS, −1.3 dBTP |
| Black frames | none | none |
| Transition frames per cut | 10 / 9 / 9 / 10, starting at the cut | 10 / 6 / 10 / 10, starting at the cut |
| Titles visible (checked by eye) | 5 / 5 | 5 / 5 |
| Title OCR match | 0.96, 1.0, 1.0, 0.21, 1.0 | 0.96, 1.0, 0.0, 1.0, 1.0 |

**How transition frames are counted.** Each output frame within ±0.6 s of a cut is compared, in the band below the titles, with the true source frame of the outgoing and the incoming clip at that instant. A frame that matches neither is "mixed". A hard cut scores 0.

**On the title scores.** Both 0.0/0.21 scores are tesseract misreads on busy backgrounds. The frame sheet shows every title.

## Findings

1. **Feasible headless.** No GPU, display or window is needed. Install takes 40–61 s. 4 renders gave 0 crashes and identical timing; the one failure was my own driver bug.
2. **Speed and memory are worse on the software GPU.** Concat took 2.2× longer (37.6–53.6 s to export 15 s, against 18.8–28.5 s) and used 2.5× the memory (2.2 GB against 0.9 GB). Both fit a free runner. For a 60 s film, expect roughly 2.5–3.5 minutes of export.
3. **Transitions are equivalent here.** Fade, slide and wipe land at the same frames, with the same length, in both engines. Concat's own advantage is its catalogue of 22 GPU transitions with stylised looks ffmpeg `xfade` doesn't have: glitch, light-leak, film-burn, whip-pan, zoom-blur, blur-dissolve. This test used only the plain ones.
4. **Titles look better in Concat with no extra work:** a larger bold display font, a rounded translucent plate, automatic line wrap and a shadow. The ASS titles are smaller and plainer. Our premium path, though, already draws its kinetic type in Remotion, not ffmpeg, so this gain only matters for the ffmpeg-assembled pipelines.
5. **Concat bug: keyed offsets are doubled.** A title at `offsetY −0.30` with `offsetY` keyframes is drawn at about −0.60, off the frame, in both `preview_frame` and the export. Concat's source documents keys as absolute, so this contradicts the docs. Titles with no keys, opacity keys or scale keys render correctly, and so does a centred title. Reproduced in `title_probe.py` (run 39891782805, `title_probe/*.png`). Workaround: keep the clip's base offset at 0 and let the keys carry the position (`840cc7b`).
6. **Audio is not mastered.** Concat's mix came out at −22 LUFS. It would still need our loudnorm master step.
7. **Licence.** AGPL-3.0-or-later. Running the unmodified binary as a separate process is fine. Modifying Concat and offering it as a network service would carry AGPL source obligations.

## What would change the verdict

Run a second test only if we want a capability ffmpeg/Remotion lacks, and measure that capability itself. Candidates:
- Concat's stylised transitions between pre-rendered Remotion shots
- local Whisper auto-captions
- background removal or stabilisation

## Regression

- Full suite on this branch, with the CI dependency set: **560 passed, 5 skipped (need credentials or optional modules), 0 failed**.
- The branch only adds `experiments/concat/` and `.github/workflows/concat-headless.yml`. No existing file changed.

## Commits

`6b82fa5` probe · `715238f` prototype · `8a36f3c` driver fix · `c8d8b94` deterministic media, frame-exact classifier, title probe · `840cc7b` title workaround.

## Output hashes (run 39892495208)

- `concat_15s.mp4`: SHA256 prefix `8323d94d6a332577`
- `baseline_15s.mp4`: SHA256 prefix `41ee3cfeeee3ceda`
