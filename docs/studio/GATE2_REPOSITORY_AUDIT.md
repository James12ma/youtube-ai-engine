# Gate 2 — Repository audit and architecture decision

Status: **complete, awaiting owner approval.** No production code was changed for this audit.
Audited: `main` @ `79722aa` (2026-10-20), all 40 remote branches, all 18 PRs, and the 40 most recent Actions runs.

## 1. What exists (verified)

**Scale:** `main` has 341 tracked files and ~30.8k lines including JSON plans, plus 39 GitHub Actions workflows. On top of that, 13 feature branches carry another 0.5k–3k lines each, all unmerged.

**Runtime architecture on `main`:**

```
Telegram (owner only) ──► Cloudflare Worker alan7_bot (D1: jobs/events/meta)
                              │ workflow_dispatch (GitHub API)
                              ▼
                 GitHub Actions on public-repo runners (one workflow per job type)
                   research → verified script → storyboard → render (Piper/Kokoro, ffmpeg, Remotion, Blender)
                              │
           encrypted pack pushed to qa/<run_id> branch  or  private Telegram delivery
Kaggle free GPU (Wan2.2-TI2V-5B "LENA" test, owner-approved single generations)
```

**Tests:** I ran the CI dependency set (`requirements*.txt` ×5, Playwright Chromium) with `python -m pytest -q -rs`. Result: **479 passed, 5 skipped** (3 live-API keys absent, 2 need espeak) in 119.7 s. The suite is large and green, but it verifies contracts and data flow, **not picture quality**. No test can catch "slideshow".

**Security:**
- A full-history scan of every branch for Google/GitHub/OpenAI/Groq/Telegram token and private-key patterns found **nothing**.
- The bot only serves `OWNER_ID` in a private chat and verifies Telegram's `secret_token` header.
- Secrets live in Cloudflare/GitHub secrets. The repository is **public**, so outputs are delivered encrypted (`qa/*` packs) or privately via Telegram.
- The README notes that credentials once exposed still need rotation. That item stays open.

## 2. Root-cause diagnosis of the observed failures

The owner's 13 symptoms come from **three structural causes**, not from bugs.

### Cause 1: the director's data model cannot express a film

The storyboard contract that feeds rendering (`pipeline/models.py`) is:

```python
class Scene: index, section_index, start_s, end_s,
             visual_type: Literal['screen_recording','diagram','text_overlay','chart','broll'],
             instruction: str, claim_ids, search_terms
```

It produces one visual per script section, chosen from 5 coarse categories, plus a free-text instruction. It has no shot list, no entities or characters, no actions or state changes, no camera, no transitions, and no word-level binding. Whatever renders it can only make a **slideshow**. That covers symptoms 1, 2, 3, 4, 5, 6, 8, 9 and 13.

### Cause 2: the "Semantic Film Director" is a single-story demo, not a general planner

`tiktok_motion/semantic_director.py` (PR #18, plus copies on `feat/semantic-film-director-*`, `test/cinema-acceptance-*` and `feature/gods-eye-view-integration`) is a regex compiler:
- 6 hard-coded actions (`establish/compose_send/transmit/receive/review/invite`)
- a fixed cast (`Applicant`, `Recruiter`, `APP-042`)
- hard-coded camera rectangles

Any other script returns `needs_visual_asset`. Its own report says `pixel_relevance_verified: False` and `demonstrated_scope: 'Applicant-phone-recruiter communication; not unrestricted film generation'`.

It is honest and fail-closed, and its ideas are worth keeping: an entity registry, prop state transitions, and word-timed action binding. But it is the kind of disconnected demonstration the mission rules out.

### Cause 3: rendering is a collection of per-niche one-off renderers with no shared editor

The repo has at least 9 independent render paths, each with its own layout logic:
- `channel/video.py` (narration + cards)
- `channel/documentary.py` (licensed clips + xfade)
- `scripts/render_educational.py`, `render_web_explainer.py`, `render_showcase.py`, `whats_new_plan.py`
- `tiktok_motion/render.py` (Pillow), `career_motion.py`, `reference15/produce.py`
- `tiktok_motion/premium/` (Remotion + Blender)
- the God's Eye capture (Cesium → Remotion)

None of them shares a timeline model, transition logic, typography system or audio mix. Every new niche became a new renderer instead of a new **capability** inside one editor, which is why quality is inconsistent (symptoms 7, 10, 12, 13).

**Related process problem:** several agent sessions are working **in parallel** on overlapping branches (`feat/semantic-film-director-20261020`, `feat/hybrid-cinematic-story-scenes`, `test/cinema-acceptance-20261020`, `feature/gods-eye-view-integration` pushed today, `feature/finance-integration-reviewed`). They duplicate `semantic_director.py`, `SemanticFilm.tsx` and `premium_job.py` with diverging contents. A reconstruction needs **one integration branch** and those sessions paused or re-pointed. Otherwise architectures will fork again.

## 3. Subsystem classification

| Subsystem | Location | Verdict | Evidence / reason |
|---|---|---|---|
| Telegram owner bot (Cloudflare Worker + D1) | `alan7_bot/` | **KEEP → REFACTOR** | Owner auth, webhook secret, persistent `jobs/events`, retry of failed dispatches and Miniflare tests are solid. But the 885-line single file mixes SEO, scripts, motion and director commands. Split it into modules and add a `film` job kind. |
| Job dispatch via GitHub Actions | `.github/workflows/` (39) | **REFACTOR** | Free on a public repo and works. But there are 39 single-purpose workflows. Consolidate into ~8 parametrised ones: `studio-job`, `asset-gpu` (Kaggle), `ci`, `bot-test`, `bot-deploy`, `delivery`, `cleanup`, `diagnostics`. |
| Research + source-verified script pipeline | `pipeline/`, `verification/`, `router/`, `adapters/` | **KEEP** | Claim extraction, NLI/number checks, free-provider router with quota pacing; live-passed per `docs/LIVE_PIPELINE_PASS_2026-10-16.md`. It becomes the Research and Scriptwriter stage. |
| Storyboard model `Scene/StoryboardOutput` | `pipeline/models.py` | **REPLACE** (as render input) | Cause 1. It stays only as a legacy artefact. |
| `channel/director.py` (SEO/title director) | `channel/` | **KEEP** (rename the role) | It's a packaging/SEO reviewer, not a film director. Keep it as the packaging stage. |
| Semantic film director (regex) | `tiktok_motion/semantic_director.py`, `story_scene.py` | **REPLACE** | Cause 2. Its registry, state-transition and word-binding concepts carry into the new spec. |
| Narration: Kokoro (native word timings), Piper, Chatterbox | branches + `tiktok_motion/reference15`, `narration_pro/` | **KEEP → REFACTOR** | Kokoro word timings are exactly what word-synced editing needs. Consolidate into one Voice Director module with a per-language voice choice; Spanish quality needs an owner listening test. |
| Captions / alignment | `narration_pro/captions.py` | **KEEP** | Feeds the subtitle and kinetic-type tracks. |
| Real screen recording (Playwright web apps; LibreOffice Calc native keyboard) | `production_pro/recorder.py`; `production_pro/sheet_recorder.py` on PR #1 | **KEEP** | Records real interactions, not screenshots. This is the base for Gate B. PR #1 is 9 days stale and needs merging into the new branch. |
| Documentary footage (Commons, Pixabay, NOAA discovery; licence gate; xfade) | `channel/documentary.py`, `channel/commons.py`, `pixabay.py`, `scripts/footage_discover.py` | **KEEP** (sourcing) / **REPLACE** (editing) | Licence gates and discovery are valuable. Its own ffmpeg xfade editor gets replaced by the shared editor. |
| Visual QA scorer (CLIP + OWL-ViT) | `channel/visual_qa.py` | **KEEP → REFACTOR** | A real pixel-level relevance check. It becomes part of the Quality Inspector (runs on runners; HF is blocked in this sandbox). |
| Remotion + Blender premium kit (Focus) | `tiktok_motion/premium/` | **KEEP** (components) | `Kinetic.tsx`, `Dialog.tsx`, cursor, the film finish and the Blender studio-object pipeline are proven building blocks for World 2. `OwnerPremium.tsx` / `SemanticFilm.tsx` get superseded. |
| God's Eye geographic capture (Cesium, offline NaturalEarth) | `feature/gods-eye-view-integration` | **KEEP** (as a capability) | Rendered 12 s narrated route video with word-timed actions (per its own validation doc; I haven't seen the video). It becomes the `map_route` capability. |
| Kaggle GPU generation (Wan2.2-TI2V-5B) | `kaggle/` | **KEEP (experimental)** | Free GPU path with encrypted reference transfer. No recorded quality result found in the docs. The same channel could run free **image** models for photoreal stills (reference capability C3). |
| Pillow renderers & demos | `tiktok_motion/render.py`, `premium_demos.py`, `render_demo.py`, `run_task7/8_*` | **REMOVE** | Source of the flat "boxes and text" look. Archive, don't delete history. |
| Per-niche render scripts | `scripts/render_*.py`, `career_motion.py`, `reference15/produce.py`, `channel/video.py` | **REPLACE** | Cause 3. They migrate into capabilities of the single editor. |
| One-off plans & root task reports | `plans/*.json`, `TASK*_AUDIT.md`, `README_TASK*.md`, `demo_report.json` | **REMOVE** (move to `docs/archive/`) | Historical. They clutter the entry points. |
| `qa/*` encrypted review branches (7) | remote | **REMOVE** (owner decides) | Delivery side effects, not code. `qa-cleanup.yml` already exists. |
| Owner-upload / YouTube release gates | `channel/oauth.py`, `metadata.py`, `packaging_lint.py`, approval digests | **KEEP** | Publication stays owner-gated, as required. |

## 4. Architecture decision: **Option A, Deep Reconstruction**

**Decision:** keep the governance, research, verification, voice, sourcing, recording and bot infrastructure. Rebuild the **director → spec → editor** core that the failures trace back to.

Why not B (Clean Rebuild):
- The parts that work are expensive to rebuild and already battle-tested: 479 green tests, live-passed research pipeline, owner-only bot with persistent D1 jobs, encrypted delivery, licence gates, real screen recording, word-timed TTS.
- The failure is **concentrated** in one seam: storyboard model + director + fragmented renderers. A clean rebuild would throw away working safety infrastructure to fix a problem that lives in a well-bounded layer.

What A means concretely: a new `studio/` package becomes the single production path. The old renderers are frozen and retired as their capabilities migrate.

```
script ─► Director (LLM via free router, staged)          ─► Cinematic Production Spec (validated JSON)
            beats → visual counterparts → shots →                │ entities/locations registry, actions with
            technique per shot (only from Capability Registry)   │ state before/after, narration word span,
                                                                  │ camera, transition, technique, assets
          capability gap? → fail closed, report to owner          ▼
Voice Director (Kokoro word timings) ──► bind actions/cuts to real word times
Asset Producers (cached by hash): AI stills (Kaggle GPU), Blender objects, licensed footage, screen capture, Cesium
Editor (one Remotion "Film" composition): multi-track timeline, kinetic type track, transitions, VO/music/SFX mix, subtitles
Quality Inspector: technical (ffprobe, loudness, black/freeze), spec coverage (every action on screen in its
                   word span), visual relevance (CLIP/OWL on runner) ─► report; NEVER approves
Orchestrator: existing D1 job state + Actions dispatch, stage-level resume via artifact hashes
```

The capability registry is how the mission's "story over templates" rule gets enforced in code. The director can only assign techniques the registry declares renderable. Anything else becomes an explicit **capability gap**, never a silent substitute.

## 5. Expected quality limits and costs (honest)

- **Money:** $0 additional. Uses public-repo Actions runners, the owner's free Kaggle GPU quota, the Cloudflare free plan, and free LLM tiers through the existing router. **The free-tier limits could not be re-verified live**: kaggle.com, docs.github.com and developers.cloudflare.com are unreachable from this sandbox. They'll be checked on the runner or by the owner before relying on them.
- **The biggest quality risk is photoreal story imagery (capability C3).** Without a working free image model on Kaggle, the reference's dark "story world" can't be produced, and videos are limited to motion graphics and licensed footage. This is the first thing Gate A has to prove.
- **CPU rendering is slow** for Blender Cycles (~30 s/frame at 1080×1920 on 4 cores, measured). Mitigation: render reusable 3D objects once (asset library), use the Kaggle GPU for Cycles, and keep shot motion mostly 2.5D in Remotion (fast: 390 frames in ~3 min, measured).
- **Spanish narration quality** with free voices is unproven and needs owner listening.
- **Real people and brands** (as in the reference) need licensed material. The system will default to original or fictional subjects.
- **Generative video** (Wan2.2 on Kaggle) is treated as experimental. No quality result has been recorded in the repo yet.
