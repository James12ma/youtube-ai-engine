# HANDOFF

Last updated: 2026-10-22. Read this first when resuming.

## Where things stand

- **Phase 4 (Gate A) in progress.** The owner approved the reconstruction on 2026-10-22 and gave full access. WanGP is the generation engine.
- **Pipeline (`studio/`):**
  - `director.py`: free LLMs (Gemini 3.8 flash → 3.1 flash-lite → Groq gpt-oss → OpenRouter), with retries, repair from the best attempt, and fail-closed behaviour.
  - `spec.py`: validator. Words covered contiguously, ≤ 14 words per shot, beats inside their words, state chains, every asset has an AssetRequest, typed UI screens.
  - `capabilities.py`: technique registry.
  - `voice.py`: Kokoro word timings, aligned.
  - `assets.py`: WanGP GPU requests, with identity text and seed per character.
  - `gpu/wangp_job.py` + `gpu/kaggle_run.sh`: WanGP API on the Kaggle T4.
  - `timeline.py` + `editor/`: Remotion; one composition for every spec.
  - `inspector.py`: delivery, loudness, black/freeze and coverage checks, plus a beat sheet; it never approves.
  - `render.py`: stage → render → master (−14 LUFS) → inspect.
  - `deliver.py`: private Telegram.
  - `order.py`: hash-verified private scripts.
- **Workflows:**
  - `studio-gpu.yml`: request files.
  - `studio-cpu.yml`: voice/director jobs.
  - `studio-film.yml`: a full order → MP4 → Telegram.
  - All results are encrypted to `studio/keys/*.pub.pem` and pushed to `studio-assets/<run>`. Decrypt with `studio/gpu/decrypt_assets.sh <run> <key> review_session <dir>` (the session private key lives only in the scratchpad).
- **Telegram:** `/film` is in `alan7_bot` (41/41 bot tests). **Live.** Deploy run 39797623314 finished every step before its cancel took effect, so the deployed bot already answers `/film` (the owner's screenshot confirms the usage reply). A bare `/film` only shows usage; the full script must follow on the same message.
- **Verified live:**
  - The Kokoro voice job ran: 29.6 s, 71 words aligned.
  - The Director produced a valid 10-shot spec after 2 repairs (`studio/films/gate_a_director/`).
  - The Kaggle dispatch, fetch and encryption loop works end to end.
- **Gate A delivered:** pipeline run 39794737218 (14 min, $0, Telegram delivery OK). v2 fixes a white flash and was sent in chat. Owner verdict pending; see VISUAL_ACCEPTANCE.md.
- **GPU facts (Kaggle 2× T4):** Z-Image Turbo still = 14 s warm, 102 s cold. The Wan 14B I2V model is too heavy. Generated video stays experimental; the next probe should try lighter I2V (LTX-2 distilled GGUF, Wan Fun 1.3B) with per-task timeouts.
- **Tests:** full suite 498 passed / 5 skipped after merging main, plus later studio tests (25 + 4 + 9). Bot: 41/41.
- **Branch:** `ccr-ff883983-8z1psm`, based on `feature/tiktok-motion-engine` (PR #3 head). Nothing merged, published or deployed. No money spent.
- **Reports:** `docs/studio/GATE1_REFERENCE_ANALYSIS.md` and `docs/studio/GATE2_REPOSITORY_AUDIT.md`.
- **Visual record:** `VISUAL_ACCEPTANCE.md`.

## Key commits on this branch

| Commit | What |
|---|---|
| `8a4b45a` | Focus prototype source (Blender scene, Remotion project, audio synth, render.sh, qa.py, tests) |
| `1ef8daa` | BT.709 delivery encode fix, QA report, evidence frames |
| (this commit) | Gate 0–2 reports, PROJECT_PLAN.md, HANDOFF.md, VISUAL_ACCEPTANCE.md |

## Environment facts that matter (this cloud sandbox)

- 4 CPU, no GPU, 15 GB RAM. Blender via `pip install bpy==5.2.2` (Cycles CPU only; EEVEE needs EGL/GPU).
- npm and PyPI reachable. **Hugging Face, OpenAI model CDN, kaggle.com, GitHub raw/release downloads and vendor docs are blocked.** Model-dependent work (ASR, CLIP, depth, image generation) must run on GitHub runners or Kaggle.
- Remotion needs `--browser-executable=/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell`.
- The container has restarted twice mid-render. The file system survived both times. Long renders must be resumable (render.sh skips finished frames).

## Verified test results

- `main` @ `79722aa` with the CI dependency set: **479 passed, 5 skipped** (`python -m pytest -q -rs`, 119.7 s).
- This branch: `tests/test_tiktok_premium_prototype.py` 4/4 pass. `tests/test_tiktok_visual_director.py::test_specialized_routes` and `tests/test_tiktok_motion.py::...test_visual_director_routes` **fail on the base branch too**, because they assume Manim/Motion Canvas are installed.

## Coordination warning

Other agent sessions push to overlapping branches (gods-eye pushed 2026-10-21; semantic-film, cinema-acceptance and finance pushed 2026-10-20). `main` already contains an adapted copy of the Focus prototype (PR #16). Before reconstruction, the owner should confirm a single integration branch.

## Next actions (only after approval)

1. Create the `studio/` package: spec, registry, director, voice, assets, editor, inspector.
2. Prove AI-still generation on the free Kaggle GPU (quality test, licence check).
3. Render the Gate A film. Record it in VISUAL_ACCEPTANCE.md. Send it to the owner. Stop for acceptance.
