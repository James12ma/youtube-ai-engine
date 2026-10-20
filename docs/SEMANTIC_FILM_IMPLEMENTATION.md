# Semantic film implementation and verified scope

Extends PR #18 and the existing premium private pipeline. No main merge, production Worker deployment, external service provisioning, paid API or publishing is part of this change.

## Architecture audit

- `premium_job.make_plan -> narrate -> Remotion OwnerPremium -> technical QC -> premium_private_job -> Telegram` remains the production boundary.
- PR #18 added seven illustrative shot types, but its original conditional JSX did not compile. This continuation fixes that error and preserves the seven modes and legacy layouts.
- Existing LogicScript screen recording, charts, narrated lessons and Alan7 verification code remain intact and are covered by the repository regression suite.
- Blender's existing Focus composition is preserved. It is a separate fixed composition, not a universal 3D scene generator. New communication scenes use original SVG vector environments and people; they do not masquerade as Blender renders.

## Working implementation

`semantic_director.compile_script` parses ordinary English communication sentences into establish, compose/send, transmit, receive, review and invite actions. It keeps exact words and punctuation, source hash and original voice. Missing actions, unsupported scenes, reordered causes and unsourced factual quantities are blocked with explicit requirements; no cards are substituted.

A persistent registry binds applicant, recruiter, phone case, company office and application APP-042 to original procedural artwork. The compiler produces six granular shots from the four original sample sentences. Word timestamps come from the actual generated Kokoro narration. No proportional action timing or ASR verification is claimed.

The Remotion film implements room and desk environments, laptop listing/application state, character eyes/breathing, phone/finger interaction, draft/sending/sent UI, a once-only moving application packet, matching company office, recipient notification, review and split-view invitation. It reuses the same phone geometry across the macro/network match, adds camera pan/push/macro movements and short continuity dissolves, and creates low-level original click/notification sounds at speech action cues.

## Automatic quality boundary

Structural gates reject wrong application IDs, changed character appearance, action ordering, unsupported actions, narration/shot mismatch, blank simulation labels, gaps and out-of-range action timing. Render checks inspect codec, dimensions, duration, full decode and three pixel samples per shot for black/static execution. Pixel change is not a semantic vision model: camera motion alone may satisfy it. Human visual relevance, UI legibility and physical plausibility remain independent review criteria.

## Telegram integration and isolation

New `/film education en <complete script>` and `/filmtest` commands use the existing owner-authenticated private script document transport and D1 queue. Supported profile tags: children, finance, news, education, technology, documentary. These tags do not create an unrestricted asset generator: the executable communication vocabulary is still bounded.

`CINEMA_REVIEW_REF` directs only cinematic jobs to an explicitly configured review branch; existing premium/Director jobs retain their main routing. The live acceptance harness runs the actual Worker inside workerd/Miniflare with local D1, real private Telegram file storage and actual GitHub branch dispatch. It tests unauthorized ingress, non-owner rejection and duplicate suppression. Its optional test-only proxy adds the owner's public encryption key to preserve private review delivery. Production Worker remains unchanged pending owner approval.

## Not yet implemented or demonstrated

- Open-ended LLM scene planning across arbitrary subjects, real licensed footage retrieval, generated realistic environments, 3D people, lipsync, arbitrary object interactions and geographic map accuracy.
- Arbitrary children's animation, finance/news factual evidence acquisition, or automatic citation verification. Unsupported factual scenes fail closed rather than inheriting the communication renderer.
- Semantic mixing of Blender, documentary footage and LogicScript recordings in one fully generated timeline. Existing engines are preserved; a universal cross-engine compositor remains future work.
- Independent ASR, pixel-level semantic model judgement and a guarantee of professional cinematic quality.

## Reproducible checks

```bash
python -m pytest -q
npm test --prefix alan7_bot
(cd tiktok_motion/premium/remotion && ./node_modules/.bin/tsc --noEmit -p tsconfig.json)
```

Runtime dependencies and real browser installation follow the existing offline CI workflow. Local browser downloads can be unavailable in the workspace; the verified free public Ubuntu runner is the authoritative browser-test environment.

Live render evidence and shot-by-shot visual evaluation are recorded after the actual MP4 is reviewed.
