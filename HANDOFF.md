# HANDOFF

Last updated: 2026-10-21. Read this first when resuming.

## Where things stand

- **Phase:** stopped after Gate 2, **waiting for owner approval** (see PROJECT_PLAN.md → "Owner decisions needed").
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
