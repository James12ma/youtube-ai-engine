# Editorial reference — Micro-detail cinematic storytelling (owner-supplied 77 s example)

Date: 2026-10-20. Source: user's reference video supplied in the chat as `164485.mp4` (77.36 s, portrait 9:16). This documentation describes the cinematic grammar we should learn from. It does **not** reproduce or license the original video and does **not** verify its surveillance-related factual claims.

## User's desired bar

Produce a cohesive mini-documentary or explainer in which every narrated concrete event has visible causes and consequences. Premium design is not an array of beautiful cards; it is a sequence of **specific actions**, spatially and temporally consistent, with enough tiny annotated details that a viewer understands how a system works. Blend map/real licensed footage, 2D illustration, 3D modeling, UI/technical overlays, diagrams, screen simulations, charts, documents, and people *when appropriate*. The engine chooses the visual technique scene-by-scene; it must not force all subjects into one template.

## Time-coded observations from the reference

| Time | Visible visual mechanism | What this teaches our system |
| --- | --- | --- |
| 00–05 | Overhead city/crowd view; framing overlays and street labels | **Geographic establishing shot** before technical detail, retain an identifiable anchor |
| 05–09 | Change to side-on helicopter-and-tower diagram; clear vertical 300 m marker | Change camera plane to explain height and position; measure only with cited sources |
| 10–17 | Helicopter flies across a stylized sky; push toward the small ball under its front; circle highlights the component | **Macro-detail transition**: wide vehicle → one physical part, with smooth focus transfer |
| 18–23 | Optical sensor ball isolated on dark technical grid; circular rotation arrows; nested lenses labeled and zoomed | **Exploded/detail functional view**: show exact mechanical movement and component relationships, not generic labels |
| 24–35 | Return to same aerial city view with receding zoom, curved route, concentric search rings, location markers, distance values, illustrative plate | **Shared spatial memory**: same setting, progressive overlays, dynamic visual proofs; illustrative measurement is not verification |
| 36–49 | Color-to-thermal/sensor view, split-frame comparison, heat-point schematic, tracking brackets, stabilization/tracking HUD | Transform the **same subject** to compare modalities and reveal a hidden mechanism; any simulation must be labeled |
| 50–55 | Helicopter + directional data chain to a building, then people looking at tactical displays in a command room | Visualize communication as a causal route **sender → transmission → recipient → action** |
| 56–59 | Map reappears and region is annotated with an incident/highlight | Reuse environment to show an operational consequence rather than cut to a new unrelated picture |
| 60–69 | Microphone and face prohibition icons, authorization document, hourglass | Move from technology to process/constraints; icons and documents remain legible and sourced |
| 70–73 | Street-level view between tall buildings with helicopter overhead, direct question to viewer | Return from abstract aerial explanation to a concrete human-scale POV; payoff links back to opening |
| 74–77 | TikTok app end-card in supplied sample | Platform-branded outro is NOT to be copied; use owner brand / review-safe ending |

**Facts vs effects:** The reference visually depicts a sensor, thermal image, camera tracking and numeric distances. These shots should not be treated as proof that those exact surveillance capabilities/distances/permissions are real. Our system needs a claims ledger and source check whenever it uses numbers, laws, security capabilities, quotations, or sensitive stories.

## Required production principles (not just style prompts)

1. **Narrative causality:** Track agents, props and changes of state (who does what, to what object, where the information goes, what happens next). Each shot has an explicit communication/explanation purpose.
2. **Shot grammar:** Choose establishing → medium/action → macro/mechanism → visualization/comparison → outcome → audience-scale POV as the story demands; vary composition while preserving continuity.
3. **Micro-animation:** Animate controls and details of the subject itself: device screen states, cursor click, antenna pulse, lens gimbal rotation, dashed data packet route, highlight ring, vehicle motion, camera zoom, notification received, graph trace. Not just moving text.
4. **Persistent entities:** A person, phone, document, or vehicle retains a stable ID and appearance/shape/position across connected shots. Visible motion should respect a shared timeline, direction, and geography.
5. **Cross-shot transitions:** Camera zooms to a physical component; the component transforms into a technical cutaway; the technical diagram returns to the real-world environment. Avoid arbitrary wipes and jump cuts between unrelated cards.
6. **Selective overlays:** Distance scale, trace, arrows, labels, circles, face/eye-line, on-screen coordinate and subtitle placement should be synchronized to the exact narration beat. Information hierarchy matters more than overlay count.
7. **Cinematography:** Lighting, depth, clean typographic hierarchy, sound effects, spatial UI, and intentionally variable shot length. Premium can mix flat 2D illustration with real footage and rendered 3D; it does not require photorealism in every shot.
8. **Evidence / provenance:** Visual evidence, real stats, geographic maps, official documents, interviews and photographs require source lineage. Separate sourced fact, schematic illustration and AI-generated reenactment (label the latter). Never invent precise distances or legal rules.
9. **Owner control:** Keep Telegram script input, private preview and explicit review gate. Preserve original narration verbatim and protect LogicScript and Alan7. No YouTube upload or paid compute without permission.
10. **No lazy fallback:** Unsupported requested cinematic action is marked `needs_visual_asset` or `needs_owner_review`. Do not silently substitute four repeated glossy title cards and claim completion.

## Proposed shot contract for Work

Extend the existing screenplay schema to describe each timed beat with:
`shot_id`, `narration_range`, `source_sentence`, `purpose`, `scene_kind`, `location_id`, `subjects:[{entity_id,role,appearance_ref}]`, `props:[{entity_id,state_before,state_after}]`, `action`, `camera:{framing,movement,target}`, `overlays:[{text,anchor,start,end,source_id}]`, `transition:{from_shot,continuity_object,match_point}`, `asset_requirements`, `evidence_source_ids`, `rendered_visual_check`, `needs_owner_review`.

Action beats must be granular enough to specify **which visual component moves, in which direction, when, and why**. Avoid a planner response that merely chooses `kind: cards`.

## Our acceptance challenge: candidate → phone → recruiter

Use the existing structured sample `examples/hybrid_applicant_recruiter.json`, but produce a new shot plan with at least these *observable* cause-and-effect beats:

1. Establish room + candidate + laptop showing a **clearly fictitious** job listing; camera pans from candidate to phone.
2. Candidate opens messaging/application interface; cursor/finger activates a send action; the phone screen visibly changes from draft → sending → sent (do not claim real delivery).
3. Match-cut to phone antenna / stylized packet/connection visualization; animated signal traverses a readable path toward the **same company office**.
4. Continue the signal across a second matching device at recruiter's desk; notification arrives with the corresponding job application identifier.
5. Recruiter interacts with notification and screens a **fictional** application; visible recipient action follows visibly from received message.
6. Return to two human/phone viewpoints for contact/interview invitation; use a neat split-screen or shot-reverse-shot, preserving actors/props.

Include 1 macro detail view (device interaction), 1 spatial diagram (signal), 1 human close-up, a transition carried by the **same object**, at least 2 distinct camera movements, and 1 labelled visual simulation. User text/voice unchanged. This is an acceptance target; **not** a claim that it can currently be rendered.

## QA rubric / failure conditions

Score each visual shot on five independently observable criteria, each 0/1:
- Script-grounded action occurs on screen (rather than generic text or random icon).
- Subject/prop identity is consistent with previous connected shot.
- Camera/composition visibly supports the concept being explained.
- Annotations animate at the relevant moment and remain readable.
- Evidence and simulations are correctly attributed/labeled.

Any false factual data, wrong correspondence between sender and receiver, missing required action, illegible key UI/overlay, or broken continuity is a **blocking** failure (even if the overall video is visually beautiful). Owner review is required. Track recurrence of the same scene layout and demand visual diversity when narration changes subject.

## Handoff boundaries

PR #18 is currently a draft vector-animation **foundation**; it does not already implement the requested cinematic rendering or the reference's micro-animations. Work must separately validate live render, improve timeline, semantic planner, continuity and real asset integration, and deliver a reviewed MP4 plus a shot-by-shot QA report. No new repo, no branch overwrite, no paid services, no automatic publishing and no merge without owner approval.
