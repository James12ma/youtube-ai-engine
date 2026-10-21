# PROJECT PLAN — Universal Autonomous Cinematic Studio

Branch for this work: `ccr-ff883983-8z1psm` (isolated; nothing merged to `main`).
Budget: **$0 additional**. Publication, merging, deployment and spending all need explicit owner approval.

## Gate status

| Gate | What | Status |
|---|---|---|
| 0 | Inputs and access | **Done.** Gaps: only 1 reference video supplied; earlier outputs from other sessions are encrypted or Telegram-only; no ASR models reachable in this sandbox. |
| 1 | Reference analysis | **Done**: [`docs/studio/GATE1_REFERENCE_ANALYSIS.md`](docs/studio/GATE1_REFERENCE_ANALYSIS.md) |
| 2 | Repository audit + architecture | **Done**: [`docs/studio/GATE2_REPOSITORY_AUDIT.md`](docs/studio/GATE2_REPOSITORY_AUDIT.md). Recommends **Option A (Deep Reconstruction)**. |
| — | **Owner approval of the audit, architecture and plan** | **WAITING.** No reconstruction until approved. |
| A | Cinematic visual quality MP4 (15–30 s, narrated) | Not started. Owner acceptance required. |
| B | Real screen tutorial MP4 | Not started. Owner acceptance required. |
| C | Documentary segment MP4 | Not started. Owner acceptance required. |
| D | Telegram → MP4 end to end | Not started. Owner readiness acceptance required. |

## Execution plan after approval

### Phase 4: Gate A (prove the visual engine)

Build only the core needed for one real film, all as reusable `studio/` modules:
1. **Production Spec v1** (pydantic + JSON Schema): project, scenes, shots, entities/locations registry, actions with state before/after, narration word spans, camera, transition, technique, asset refs. Validator fails closed.
2. **Capability Registry v1** with 5 techniques: `kinetic_type`, `ui_flow` (form/dialog/cursor/state change), `still_2_5d` (AI still + push/parallax), `object_3d` (Blender asset library), `vector_motion` (dots/arcs/arrows/charts).
3. **Director v1**: staged LLM planning through the existing free router (beats, then visual counterparts, then shots, then techniques), constrained to the registry. Writes the spec and a capability-gap report.
4. **Voice Director v1**: Kokoro with native word times, binding cuts and actions to words.
5. **Asset producers v1**: AI stills on the owner's free Kaggle GPU (open-licence model; exact model to be decided by a quality test), plus Blender object renders (cached).
6. **Editor v1**: one Remotion `Film` composition (multi-track, kinetic type track, transitions, VO + music + SFX mix, burned subtitles optional).
7. **Inspector v1**: ffprobe/loudness/black/freeze checks, spec coverage, CLIP relevance on runner, report.

**Proposed Gate A film:** ~25 s, original and fictional (no real brands or people). It uses the owner's own micro-detail example (applicant fills in a form on the phone, presses Submit, confirmation, data travels, company system receives, recruiter opens and reviews), in the reference's two-world style: a dark photoreal story world and a white explanation world, word-synced type, cuts every ~2 s. It should be judged side by side with the reference.

Gate A exit: the MP4 passes the Inspector, **and the owner explicitly accepts it.** On rejection: record it in VISUAL_ACCEPTANCE.md, find the root cause, fix the capability, re-render.

### Phase 5: core platform
Generalise the director, add capabilities (`map_route` from God's Eye, `footage` from documentary sourcing, `screen_capture` from the recorders), and retire the old renderers.

### Phase 6: Gates B and C
- **B:** Calc and web tutorials through `screen_capture` (merge PR #1's native Calc recorder).
- **C:** licensed wildlife footage through `footage`, with real subject-behaviour selection and Visual QA.

### Phases 7–8: orchestration + Gate D
Consolidate workflows. Add a `film` job kind in the bot. Resumable stages. A single Telegram instruction produces an MP4 delivered privately.

### Phases 9–10
Reliability, regression and security hardening; deployment proposal for owner approval.

## Owner decisions needed before Phase 4

1. Approve **Option A** and this plan, or redirect.
2. Gate A **language**: English (LogicScript) or Spanish (Alan7 / the reference). Also confirm the proposed **story**.
3. Approve using the **free Kaggle GPU quota** on your account for image generation. It costs no money but uses your weekly quota.
4. **Pause or re-point the other agent sessions** working on overlapping branches, and confirm this branch as the single integration branch.
5. Share more **reference videos** if "videos" was meant as plural, and any previously **rejected outputs** you want analysed (they're encrypted to you).
6. Policy on **real people and brands** (the reference uses both). Default proposal: original or fictional subjects only, unless the material is licensed.
