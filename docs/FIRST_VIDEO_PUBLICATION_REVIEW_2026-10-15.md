# LogicScript first tutorial — publication review, 15 October 2026

**Status: rendered review candidate; NOT authorized for upload or publication. The autonomous system is not yet fully production-ready.**

## The actual video
“Before You Automate: Test the One-Cent Boundary” — English, 407.04 seconds (about 6 minutes 47 seconds), 1920×1080. There are 1,189 narrated words, 18 chapters, real Piper speech, WhisperX CTC word timestamps and animated subtitles. The lesson uses the existing functional local application, not an impersonated third-party SaaS interface. All expense limits are explicitly invented teaching examples.

The original eight recorded checks show the opening boundary pair, normal/review branches, exact limits, category changes and invalid input. Seven additional recorded interactions operate the actual offline practice file: download, matrix navigation, real application-driven tests, a deliberate wrong expectation, one detected failure, and restoration to eleven passes. The standalone HTML needs a desktop browser but no account, paid service or installation. Chromium downloaded and reopened the actual HTML file successfully.

The delivered 1,189-word script is transparently assistant-authored and source-checked. It is NOT presented as the output of the still-unproven automated research pipeline. No padding was added merely to reach a duration target.

## Actual verification
| Check | Result |
|---|---|
| Corrected visual render | PASS — https://github.com/James12ma/youtube-ai-engine/actions/runs/38721241174 |
| Initial full Piper/WhisperX render | Technical PASS, then rejected in visual review for a clipped lab table — https://github.com/James12ma/youtube-ai-engine/actions/runs/38718897129 |
| Final complete regression | 233 passed, 3 API tests intentionally skipped; 47.55 s, commit 8fdc42a — https://github.com/James12ma/youtube-ai-engine/actions/runs/38721677894 |
| Real Chromium checks | 14 original policy cases plus the lab regression aggregate; 11 passes → one intentional failure → 11 passes, actual HTML download/reopen, full table width and last-row visibility |
| Downloaded final MP4 full decode | PASS, no decoder errors |
| Streams | H.264 / yuv420p; AAC at 48000 Hz |
| Ordered transcript alignment | 100% token coverage |
| Timed subtitle coverage | 100% of aligned word midpoints; 156 caption blocks |
| Recorded action checks | 15 passed |
| Largest recorded click / spoken cue error | 0.318 s |
| Independently measured audio | -16.08 LUFS; -1.33 dBTP |
| SHA256 of exact review MP4 | `2a9ea9bce46f37a9bf0ea46fa5f0d058958da789bd9ff8ade3a5224bf9c7ecf2` |

The action metric uses actual recorder timestamps and WhisperX cues. It is not an external laboratory AV calibration. Forced alignment does not prove perfect pronunciation. No VMAF/SSIM reference score or real audience-retention measurement is claimed.

## Separate editorial / visual review
The first long render passed technical checks but failed the separate visual review: inherited app CSS narrowed the practice table and hid its bottom rows. That defect was fixed, a real geometry regression was added, and the final render reused verified speech/timestamps instead of regenerating completed narration.

The corrected render is a useful, coherent instructional review candidate: real application outcomes, a reproducible offline lab, a visible failing-test exercise and consistent editing/captions. The clipping defect is resolved. It is suitable for owner review; a final subjective listening and editorial approval is still required before publication.

The review inspected the complete written lesson, all 18 chapter frames and a separate action sequence, with detailed lab frames for the expected/observed mismatch and restoration. The practical file makes the lesson reproducible. The teaching sequence progresses from a strong real boundary demonstration to policy, invalid inputs, a reusable matrix, money representation and server authorization. No account, payment or production-security capability is claimed.

This is a restrained instructional screencast, not a cinematic advertisement or a claim of commercial performance. Desktop/landscape playback is preferable for small interface labels. The operating-system save/double-click gestures are described on the start page, not filmed in Windows/macOS. Full subjective listening and pronunciation sign-off by the owner remains required. Piper emitted phoneme-map warnings; successful alignment and measured audio levels are not a human listening approval.

## Research-to-script root cause and fixes
The exact live quality failure was a short summary: 396 words / 158.4 seconds against the existing 1,200–1,800-word / 8–12-minute gate. Google OAuth was unrelated. Safe diagnostics now expose only the actual gate stage, fixed reason and numerical deficit, never arbitrary provider messages or credentials.

Changes preserve every acceptance threshold: explicit word budgets, schema-validated section expansion within the existing 4,096-token cap, and a final adaptive budget that counts actual emitted words after each section. The new regression models systematic under-writing and passes without padding or lowering the duration requirement. Accepted stage evidence and explicitly UNACCEPTED model drafts are checkpointed separately for diagnosis.

**Latest live research run still FAILED:** https://github.com/James12ma/youtube-ai-engine/actions/runs/38720074522 (commit 4e556c1). Five source-backed claims were extracted from two NIST publication pages; the generated script reached only 1,045 words / 418 seconds, so the unchanged script gate rejected it. That run made 12 real generation requests, all ending with HTTP 200; it did not complete storyboard/semantic verification. The source pages were abstracts/metadata, not the full NIST documents.

At its start the account reported 33 of 50 free daily requests used, 17 remaining. Further full generation was stopped to preserve the zero-cost quota. The final adaptive-budget correction in 8fdc42a passed regression tests but has NOT passed a fresh live end-to-end generation run. Therefore blocker 1 is improved and precisely diagnosed, not falsely declared resolved.

The earlier HTTP 429 was OpenRouter Gemma's Google AI Studio upstream shared-pool capacity, not broken YouTube authorization or exhausted account quota at that time. A real schema-validated Cohere free-router check previously passed. The current live checks verified the account's free status and every selected model price as zero. Existing bounded retry, cooldown and failover protections remain; the diagnostic run used one attempt per call and a strict account-aware total cap. Groq/Gemini paid-status uncertainty was not bypassed. No fake AI output or paid fallback was substituted.

## OAuth / channel / credential exposure
A fresh actual read-only check PASSED: https://github.com/James12ma/youtube-ai-engine/actions/runs/38719009246 . Google refreshed the token, confirmed the expected scope and returned **LogicScript — UC7vcWhYzuJtarRqSz7KgJgw**, with expected-channel matching true. This proves current refresh and channel access, not that credential rotation occurred.

**Rotation is NOT complete.** This browser's authorized Google Cloud credentials page still returns “Site Unavailable / Unable to access this site.” The Google Cloud client, consent screen and rotation controls could not be inspected. No Google Cloud administrative connector is available here. Existing working credentials were preserved; none were deleted or prematurely revoked. No new credential values were printed, committed, copied into deliverables or included in screenshots.

The minimum remaining security action is an owner or trusted administrator performing a secure replacement cutover through the Google Cloud OAuth interface and GitHub's three existing Secrets, followed by a new read-only check. No secret values should be sent in chat. An owner login in a separate phone browser does not automatically grant this session access. I cannot claim this inaccessible operation has been completed.

## Publication preparation and owner decision
Prepared title: **Boundary Testing Tutorial: The One-Cent Test (Free Browser Lab)**. The package contains the branded thumbnail, English description, 18 real-time chapters, relevant tags, SRT, script, sources and factual audit. The public practice-file URL is deliberately not fabricated: the file is delivered for review, and public hosting/link insertion remains part of the approved publication preparation after the owner approves that companion asset.

The exact MP4 above and its companion materials must be reviewed before approval. The owner should listen through, check that the lesson is understandable, and approve this exact video plus the intended public companion file. Existing human editorial and release-digest gates remain unchanged. No OWNER_APPROVAL file, fake human review, completed release authorization, upload or scheduled publication was created.

## Spending and remaining blockers
No paid APIs, subscriptions, credits, GPU services or billable deployment were activated. GitHub billing showed $0 billable Actions usage and usage within the included allocation (1,893 / 2,000 minutes at the check; 0.1 / 0.5 GB storage). Those are finite shared-account quotas, not unlimited free rendering. No money was spent by these operations. No video of any visibility, comment or other engagement was uploaded/published/posted.

Remaining items:
1. Fresh successful live research → complete script → storyboard → verification after the final adaptive correction; latest live result remains a valid rejection.
2. Secure exposed-credential rotation through an accessible authorized Google Cloud interface, then verified refresh/channel cutover.
3. Owner's full listening/editorial review and explicit approval of this exact video and companion materials; final public practice URL insertion before publication.

The first tutorial is a concrete downloadable review candidate. Fully autonomous production and immediate publication are not yet verified. No success claim is made for blocked operations.

## Commits
- Safe exact gate diagnostics: https://github.com/James12ma/youtube-ai-engine/commit/3c122439c3b0c3c8741bd5513447f0f365ebbd20
- Reproducible lab and substantial tutorial: https://github.com/James12ma/youtube-ai-engine/commit/fa27dcb80404321b1e21db793a631d648ef40c66
- Bounded section expansion / actual HTML reopening: https://github.com/James12ma/youtube-ai-engine/commit/24b73aabe1db1137e4b6e4ee88eeca8e038ad495
- Relevant claims and partial evidence: https://github.com/James12ma/youtube-ai-engine/commit/4e556c166fb0289b7819b91a1e533da1d7bf1e69
- Visual-review table repair: https://github.com/James12ma/youtube-ai-engine/commit/1e11cb838b1151c25f11c8aa96211ff3a6c40712
- Adaptive actual-word budget and unaccepted draft checkpoints: https://github.com/James12ma/youtube-ai-engine/commit/8fdc42aa2e69f44c9d9bb08047994521d3e6bf99
