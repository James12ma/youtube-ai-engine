# YouTube AI Engine — verified recovery report
Date: 2026-10-15 UTC (2026-10-14 evening in America/Santo_Domingo).
Repository: https://github.com/James12ma/youtube-ai-engine (existing private repository preserved).
Executable revision: 2c5e046fddbd91df94b773b6185ebfff08198587.
Assessment: verified technical demonstration; NOT ready for unattended production or publication.

## 1. OAuth incident: observed failure, not an assumed expired token
Inspected historical OAuth run #5 (38671165949, job 116214383056), #7 (38671208667, job 116214555147), and newly executed diagnostic #8 (38672258782, job 116217870312).
All reached the real Google token endpoint; dependencies and the existing 11 OAuth tests passed. Google rejected client authentication with invalid_client.
The newer diagnostic confirms all three required secrets are present and structurally plausible, no copied JSON/quotes detected, and client secret does not equal client ID.
The workflow maps YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, and YOUTUBE_REFRESH_TOKEN correctly. ZERO_COST_ACTIONS_CONFIRMED is 1.
This rules out missing workflow variables, missing secrets, and installation failure as the observed cause.
Google documents invalid_client as an incorrect client secret; the current client ID/secret pairing must be checked. This is distinct from invalid_grant (a rejected refresh grant).
We cannot determine which stored credential value is wrong or confirm that a token belongs to that client from non-reversible GitHub Secrets. No secret readback or export was attempted.

Real OAuth refresh: FAILED, invalid_client. Correct YouTube channel identity: NOT yet verified.
Data API access, consent-screen Testing/Production status, test users, redirect configuration, and credential rotation: NOT verified.
The Google Cloud credentials page returned Site Unavailable in this browser after one reload. This is a current access limitation, not evidence that Google is down or that the owner cannot use it.

Owner's minimal phone action:
1. Open https://console.cloud.google.com/apis/credentials in your own signed-in browser and select the existing project/client used to obtain the refresh token.
2. Verify the current client ID and its matching client secret. Update those corresponding fields at https://github.com/James12ma/youtube-ai-engine/settings/secrets/actions . Paste only in GitHub's secret fields, never in chat.
3. A refresh token must be issued to that same client. Reauthorize only if mismatched, revoked, expired, or exposed. Previously exposed credentials still require rotation; this execution did not rotate them.
4. In the existing OAuth workflow, Run workflow on main. It refreshes and performs only channels.list(mine=true), never upload.
Existing Google Web OAuth Playground configurations require the appropriate authorized redirect; do not switch client types blindly. If the consent screen remains External/Testing, refresh-token lifetime restrictions may still matter after client authentication is repaired.
No terminal or software installation is required for these phone actions.

## 2. Changes made within the existing architecture
Commit https://github.com/James12ma/youtube-ai-engine/commit/10e1b7a4336ad2cec458e4fd9826f3a54d74e9d5 :
- Safe OAuth error codes and actionable diagnostics without response-body/credential logging.
- Optional upload+readonly validation and read-only actual channel verification; uploader's upload-only default unchanged.
- Optional expected channel ID check via YOUTUBE_EXPECTED_CHANNEL_ID.
- Free-provider verification workflow; no unverified account receives a generation request.
- Six OAuth recovery regressions and four free-provider safety tests.

Commit https://github.com/James12ma/youtube-ai-engine/commit/2c5e046fddbd91df94b773b6185ebfff08198587 :
- Explicit opt-in Piper-to-Edge narration fallback, real FFmpeg MP3-to-PCM conversion, validated 48 kHz WAV, actual backend reporting, bounded network timeouts.
- Existing Piper primary and WhisperX CTC path preserved. No fake speech or proportional word timestamps.
- Genuine Edge fallback workflow and four fallback tests.
- SRT export from actual timed ASS cues; thumbnail from genuine demo screenshot; validated draft metadata.
- Final render artifact includes original/normalized WAV, words, animated ASS, SRT, both MP4s, thumbnail, metadata and QC.
- Fixed missing ENABLE_LIVE_LLM mapping in the existing gated channel-draft workflow; its production account/queue/schedule gates remain closed.
- One precise SRT timestamp/text regression.

The existing native responsive layouts, action focus/zoom, rapid transitions and WhisperX-paced interactions were retained and executed, rather than replaced.

## 3. Actual GitHub Actions results
| Check | Run | Result |
| --- | --- | --- |
| Full offline CI | https://github.com/James12ma/youtube-ai-engine/actions/runs/38672699052 | PASS: 204 passed, 3 skipped in 25.95 seconds; workflow 1m38s |
| Real Piper + WhisperX + Playwright + FFmpeg, both formats | https://github.com/James12ma/youtube-ai-engine/actions/runs/38672697309 | PASS: all steps including full dependencies, CPU imports, model, browser, render and artifacts |
| Real Edge fallback voice | https://github.com/James12ma/youtube-ai-engine/actions/runs/38672901634 | PASS: intentionally unavailable Piper exercises real Edge fallback; 5.52s, 48 kHz PCM WAV |
| Real free-provider/router integration | https://github.com/James12ma/youtube-ai-engine/actions/runs/38672899596 | BLOCKED: OpenRouter HTTP 429 RateLimitError; no AI script generated |
| Real OAuth refresh/channel check | https://github.com/James12ma/youtube-ai-engine/actions/runs/38672258782 | FAIL: invalid_client; refresh and channel access remain unconfirmed |

Three API tests are intentionally skipped in offline CI because provider keys are not loaded there. The separate provider check supplied scoped keys and exercised actual metadata endpoints.
Local focused regression run: 50 passed in 2.15 seconds; Python compileall passed.
A non-fatal GitHub warning notes older action declarations target Node20 and are forced onto Node24. Jobs completed successfully; it is not the OAuth failure.

## 4. Provider and source-pipeline status
Groq and Gemini authenticate through read-only model listing and their configured model IDs exist. Their account billing/free-tier settings cannot be established from that metadata: generation remains disabled in this verification.
OpenRouter key inspection confirms is_free_tier=true. Candidate models must end in :free and every returned pricing field must be zero before any request.
The first actual request in the final check (google/gemma-4-26b-a4b-it:free) returned HTTP429. The existing persistent provider cooldown prevented the two subsequent candidates from making HTTP requests; their null HTTP statuses do not mean they were separately rejected by the service. No cooldown or safety limits were bypassed.
No paid provider/model/plugin call was made. Live AI generation and durable-cache reuse could not be confirmed.
Topic selection, claim traceability, verification, SEO, approval and integration logic pass existing offline tests. The live source-based research-to-script pipeline was NOT completed: the original queue is still disabled example URLs, and no new owner-approved real topic/source set was supplied. FREE_PROVIDER_ACCOUNTS_CONFIRMED and ENABLE_AUTOMATION remain unset.
The rendered original local expense-rule demo uses its existing authored narration (zero LLM calls). It does not represent successful live AI research/script generation.

## 5. Verified video artifacts
Original functioning application: travel 120 dollars requires manager review; lowering to 80 dollars produces automatic approval. Figures are entered example data, not business-performance evidence.
Both outputs: 17.229 seconds, H.264/AAC, 48 kHz audio, genuine Piper narration, real WhisperX CTC alignment covering all 47 ordered transcript words, 8 animated caption blocks, responsive real browser capture.
Landscape: 1920x1080. Portrait: 1080x1920.
Measured final loudness: -16.49 LUFS, true peak -1.46 dBTP for both.
Technical QC passed: detected silence ratio 0, black ratio 0; captions occupy approximately 88.4%/89.6% of runtime (expected pauses excluded). Separate ordered-token caption coverage is 100%.
Downloaded artifact SHA256 independently verified: 9d9c0e02ab55405548dd5336b7ba6d6a140bbcdfffe71d137d1d08cf9025652a.
Both downloaded MP4s independently ffprobed and fully decoded with FFmpeg without errors. Representative landscape/portrait frames and generated thumbnail visually inspected.
Landscape MP4 SHA256: 51b8924bc15d2847f5a2f322cfd53fecd0eb5ca2756b84693121771daf452c7c.
Portrait MP4 SHA256: f66fb12811bbd17ec3ae8912d0e87429d466eab585aaf3a79d6f9ffa809fffdf.
Video/audio stream durations differ by less than 0.15 seconds; no claim of reference-based VMAF/SSIM is made.
SRT, ASS, exact word JSON, raw/normalized WAV, 1280x720 JPEG thumbnail, metadata draft and QC are included in the review kit.
Edge-only smoke verifies real speech/codec, not forced alignment of that separate short voice sample.
Human listening/pronunciation, final editorial approval, voice/dataset/commercial rights and synthetic-media disclosure decision remain required. Automated quality tests do not prove originality, copyright clearance, monetization eligibility or full policy compliance.

## 6. Security, cost and approval controls
No credential values were displayed, printed, committed or added to artifacts by this execution. Logs show GitHub-masked secret mappings; new diagnostics contain safe booleans/error classifications. This is not a claim that historical screenshots never exposed credentials.
No credentials were retrieved for local storage. Existing atomic 0600 local OAuth token-writing protections were preserved and tested.
No YouTube insert/update/delete/upload call was executed. OAuth checks only token refresh and readonly channels.list.
No release received fabricated owner approval. Upload gates require owner-approved immutable digest, independent environment authorization and synthetic-media decision; public/unlisted operations require a separate gate.
No money spent, paid services activated or billable provider requests intentionally made. GitHub Free included resources and an existing Actions $0 blocking budget were verified before dispatch; no paid plan or budget was changed.
Recorded before dispatch: 1795 of 2000 included Actions minutes used, 0.1 of 0.5 GB artifact storage, net billable $0. These are an observed snapshot, not an unlimited free-hosting promise. Manual checks consumed additional included minutes; exact final usage may update later.
No YouTube video uploaded (private/unlisted/public) or published. Live trading and unrelated account operations were not performed.

## 7. Remaining blockers and readiness decision
1. Correct Google client authentication and then confirm real refresh plus channel identity. Any exposed credentials require owner-controlled rotation through secure account UI.
2. Free generation availability: OpenRouter currently rate-limited; Groq/Gemini billing-free status is unverified.
3. Real owner-approved topic/source queue, a successful source-to-script live dry run, and production editorial/rights review.
4. Exact release approval and separate upload authorization are intentionally absent.
Technical video generation is operational and demonstrated. Unattended end-to-end production and publishing are NOT ready. OAuth success criteria are NOT met; report does not represent them as complete.

Primary diagnostic reference: https://developers.google.com/identity/protocols/oauth2/web-server
Free-key/quota reference: https://openrouter.ai/docs/api_reference/limits
