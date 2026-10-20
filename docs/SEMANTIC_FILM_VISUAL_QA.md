# Applicant → phone → recruiter: visual evaluation

## Reviewed film and methodology

The benchmark preserves the exact four English narration sentences from `examples/hybrid_applicant_recruiter.json`, submitted as ordinary prose through `/filmtest`. It contains six shots over 26.9 seconds at 1080×1920, 30 fps, H264/AAC. All artwork, people, UI, company and application APP-042 are original fictional illustration/simulation. No real applicant, recruiting decision or network transaction is depicted.

Review used the start, native-word action and consequence frame for every shot, plus the laptop detail and visible sender/recipient IDs. Short transition samples intentionally include a dissolve. This review evaluates visible functional storytelling, not a claim of professional or photorealistic cinema.

| Shot / time | Visible narration-grounded evidence | Continuity and camera | Evaluation |
| --- | --- | --- | --- |
| 01 · 0–7.4 s | Applicant at desk, fictional job listing, preparation checkmarks and application on phone | Original applicant design; wide → laptop detail → same phone macro | Pass for readable fictional setup and focus transfer |
| 02 · 7.4–14 s | Finger interaction; draft → sending → sent on the phone | Same case, company and APP-042; send click uses native `sends` timing | Pass; hand is a stylized vector gesture, not a realistic hand rig |
| 03 · 14–16.77 s | Application envelope moves once from phone toward the company office along a traced route | Same case and APP-042; macro match followed by pullback | Pass as a labelled conceptual transmission, not a real network trace |
| 04 · 16.77–20.3 s | Company-side phone changes from idle to received notification | Same company; distinct recruiter appearance; push to recipient screen; OCR reads APP-042 | Pass for visible arrival and correct application correspondence |
| 05 · 20.3–22.7 s | Recruiter opens the application; CV state and checkmarks become visible | Same recruiter and device; pan/pull toward human close-up | Pass; no lipsync or real recruiting software is claimed |
| 06 · 22.7–26.9 s | Invitation travels back while applicant and recruiter remain on screen | Two clipped, stable room views; matching application ID | Pass after fixing an observed occlusion of the applicant |

The five reference criteria are assessed through these observations: concrete action, stable subject/prop, explanatory composition, readable timed annotations, and explicit simulation/provenance. This is a functional acceptance review, not an overall artistic-quality score or owner approval.

## Measured regression and automatic gates

The first real film rendered and passed the original motion/structure checks but the recruiter room background hid the applicant in the last shot. Independent image review found the defect. Clipping each split-view panel corrected it. The new known-asset visibility probe rejects the old frame (applicant 9 matching pixels versus 594 for recruiter) and accepts the corrected frame (615 and 598 before canonical color-range conversion). These are bounded palette probes, not general person detection.

OCR independently reads APP-042 on both macro device screens. Structural gates enforce source sentences, stable appearance references, action order, application state changes, contiguous shots, native action timings and simulation labels. Sampled pixel change rejects black/static execution. These checks do not verify arbitrary semantic relevance, full anatomy, every UI label, pronunciation, claims or geographic accuracy.

An actual full-range H264 test reproduces the old yuvj420p format-gate issue; canonical delivery converts it to yuv420p/TV range and a byte comparison proves the AAC narration stream is unchanged. The same normalization is wired before the existing Blender Focus QA. A new full Blender render was not used to claim arbitrary 3D support.

## Verified tests and live transport

- Free public Ubuntu CI 39509327351: final exact counts recorded in the evidence block below. The pinned TypeScript compiler passes with no errors.
- Worker regression: 41 Node tests pass, including film intake and isolated branch routing.
- Live workerd/Miniflare with real local D1 used actual private Telegram document storage and actual GitHub Actions branch dispatch. Unauthorized requests and non-owner messages were rejected/ignored; duplicate messages did not dispatch twice.
- The production Cloudflare Worker, main branch, YouTube account and publishing state remain unchanged for this mission. `/film` is a review-branch command until owner approval permits merge/deployment.

## Remaining limitations

The semantic compiler is deterministic and bounded to this communication story vocabulary. Six genre tags are accepted but do not confer universal visual understanding. Unsupported stories and unsourced factual quantities require assets/review; they do not silently fall back to cards. Open-ended LLM planning, realistic generated environments, reusable 3D humans, lipsync, arbitrary physical interactions, licensed footage acquisition, accurate geographic maps and a fully unified Blender/Alan7/LogicScript mixed timeline are not demonstrated here. Existing engines are preserved and regression-tested, not replaced.

This is an implemented, playable illustrated-film benchmark and an integration foundation. The universal premium studio remains a broader project; owner editorial approval is still required.

## Automated regression evidence

Code/render revision: `7b2b5aa20fa3a8b31d71bffc4d61e26a50efe415`.
CI run: https://github.com/James12ma/youtube-ai-engine/actions/runs/39509327351 — **522 passed, 4 skipped, 4 subtests passed**, zero failures/errors. Skips: GROQ_API_KEY, GEMINI_API_KEY and OPENROUTER_API_KEY absent; one legacy ffmpeg/espeak smoke probe. These external providers are not claimed to be tested by this change.
Worker Node suite: **41 passed, zero failed**. Pinned Remotion TypeScript compiler: **passed**.

Local workspace regression execution encountered two unavailable-Chromium failures after its browser download was truncated; the same recording tests passed on the verified free Ubuntu CI runner. This was not hidden by removing or skipping tests.

Final authenticated ingress acceptance: https://github.com/James12ma/youtube-ai-engine/actions/runs/39509546699. Real private Telegram document upload returned HTTP 200; actual GitHub review-branch dispatch returned HTTP 204. Local D1/workerd authentication, non-owner and duplicate-message checks passed. The production Worker was not deployed.

## Final canonical film evidence

- Final render/delivery: https://github.com/James12ma/youtube-ai-engine/actions/runs/39509600775 — success on code commit `7b2b5aa20fa3a8b31d71bffc4d61e26a50efe415`.
- Final transport ingress: https://github.com/James12ma/youtube-ai-engine/actions/runs/39509546699 — success; isolated job `ca01e1f2`.
- Actual MP4: 26.944 s container duration, 807 video frames / 26.9 s timeline, 1080×1920, 30 fps, H264 **yuv420p**, AAC. Full decode and six-shot rendered QA passed.
- SHA256: `ec4b42cc76171bf17c3d1b9d31c6c8408e011bf187bf925046c382decd4c4303`.
- Exact source script SHA256: `150807d25a15e82f890433e06b28ee3b13bfccf02b009b4c36512b7dfec18405`; narration_rewritten=false.
- OCR: APP-042 read on shots 02 and 04. Final known-asset visibility probe: candidate 618 matching pixels, recruiter 587; both pass.
- Real Telegram sendVideo and sendAudio both returned accepted=true. Encrypted review copy checksums and final video hash verified after download.
- Main remains `79722aab01cf622c9bdeada025caa3e70f5487bb`; PR #18 remains open. No production deployment, paid generation or YouTube publishing performed.
