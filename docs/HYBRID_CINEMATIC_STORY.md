# Hybrid premium visual storytelling — isolated implementation

Scope: Extends existing OwnerPremium Remotion composition. Does not replace LogicScript, Alan7, voice, Worker, Telegram, or YouTube publishing gates.

## Implemented in this PR
- Seven storyboard modes: character (stylized human figures), device (illustrative smartphone), signal_flow (explicit source-to-destination path), document (owner-supplied excerpt), data (supplied numeric values), map (conceptual globe, not geographic accuracy), hero (animated opener).
- Per-scene direction: named actors, setting, action, camera, endpoints, data and document excerpt/source label. Original narration preserved and SHA256 bound.
- Legacy kinetic/cards/process/ui/timeline/chart remain available. Plain prose still uses legacy composition rather than pretending arbitrary script understanding.
- Missing roles, flow endpoints, numeric measurements and document excerpts are rejected where required. Zero new paid APIs. Owner approval and auto_publish=false preserved.
- Example script: examples/hybrid_applicant_recruiter.json. Existing private Telegram intake accepts structured script text.

## Explicit limitations
These are stylized VECTOR animations, not cinematic 3D humans, lipsynced actors, actual images or photographic video. Conceptual globe is not geographic data. No generic AI-to-character renderer is claimed.

## Offline verification
- python -m pytest tests/test_hybrid_story_scenes.py tests/test_premium_integration.py -q
- cd tiktok_motion/premium/remotion && ./node_modules/.bin/tsc --noEmit --project tsconfig.json
- Only render a local preview if dependencies and Chromium are already available and no billable service is needed.
- Review first/middle/end frames for every shot, captions, overlap, scene continuity, clear actions and content source integrity.
- Compare same applicant-phone-signal-recruiter script against previous repeated cards.

## Work / next implementation mission
1. Implement an actual semantic screenplay planner from owner plain scripts to grounded shot-by-shot JSON: named actor IDs, location, props, actions, camera, changes of state, transitions, and explicit needs_review. Never invent factual data.
2. Track continuity across scenes (character appearance, wardrobe, devices, office). Bind shot beats to word timings.
3. Upgrade vector visuals to properly licensed cinematic assets and high quality human/character 2D/3D animations with verified free compute only; do not pretend the fixed Blender Focus model creates arbitrary 3D.
4. Build spatially continuous transitions for applicant -> phone -> traveling signal -> recruiter, rather than simply adjacent scenes.
5. Add semantic editorial QA: script-to-image relevance, evidence provenance, scene variety, camera continuity, pacing, typography and audio.
6. Provide profile choices kids/finance/news/technology via existing owner-private Telegram commands; no paid API, no auto publication; preserve original logic and private access.
7. Run full Python, JS and pinned TypeScript tests and a real MP4 render, with video, hashes, test counts, comparisons for approval. Do not consume paid GitHub Actions quotas. Keep this PR draft until proven.

Acceptance: a 25–40 second, four-shot narrative showing applicant preparing, sending from phone, signal crossing, recruiter receiving/responding. Real actions, not repeated cards. 1080x1920 H264/AAC with technical QC and human visual review. Original spoken text unchanged. Owner approval required.
