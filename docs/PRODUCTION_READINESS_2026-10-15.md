# YouTube AI Engine — production readiness verification
Date: 2026-10-15, approximately 00:20 America/Santo_Domingo (04:20 UTC).
Existing private repository: https://github.com/James12ma/youtube-ai-engine
Executable revision verified: 54bcceaf865859b4d61482b094ec2be69928baf9.
Assessment: OAuth and technical video samples VERIFIED; full unattended production NOT READY.

## OAuth and the actual channel
Complete job logs for OAuth #13 were inspected:
https://github.com/James12ma/youtube-ai-engine/actions/runs/38679408477
Job 116240276730, revision e9631394d698bf83215386521fb926c9d39b2c3c.
Observed oauth_refresh_succeeded=true, access_token_valid=true, upload_scope_confirmed=true and channel_access.verified=true.
The actual read-only channels.list response identifies:
- Channel name: LogicScript
- Channel ID: UC7vcWhYzuJtarRqSz7KgJgw

This confirms that Google accepts the configured client ID/client secret/refresh token combination now and that the token can read this channel. It is not an upload test.
The original #13 run had no independently configured expected channel ID. It identified the channel accessible to the owner-authorized token; it did not compare against an existing external owner target.

Set the non-secret repository variable YOUTUBE_EXPECTED_CHANNEL_ID to the observed LogicScript ID.
Executed OAuth #14 against revision 30e89aa5305306785452d97ddd79758b9f3fca6e:
https://github.com/James12ma/youtube-ai-engine/actions/runs/38680206999
Job 116242777628: PASS, 11 offline OAuth tests PASS, real refresh PASS, actual read-only channel access PASS, expected_channel_configured=true and expected_channel_matches=true.
The channel ID is now pinned for future checks. No upload/publication permissions were activated.

## Credentials exposed in earlier screenshots
Exposure is acknowledged. Credential ROTATION IS NOT COMPLETE.
Google Cloud credentials https://console.cloud.google.com/apis/credentials again returned Site Unavailable / Unable to access this site in this browser. No usable credential-management or secure sign-in form was available.
The available Google connectors do not administer OAuth clients, and GitHub Secrets do not permit credential-value readback. No secret export or retrieval workaround was attempted.
No working credential was revoked, deleted, replaced or printed by this execution.

Required owner-only capability: secure access to the existing Google project's OAuth client and consent flow, so replacement credentials can be entered directly into GitHub Secrets, verified, and the exposed credentials safely retired.
Do not send new credentials, authorization codes or screenshots containing them in chat.
Do not blindly revoke an old refresh token after generating a replacement under the same project: Google's documented token revocation invalidates the project's access/refresh grants across its clients, which can invalidate the replacement too. A deliberate rotation/cutover must respect this behavior.
Reference: https://developers.google.com/identity/protocols/oauth2/web-server#tokenrevoke
The working connection was preserved, but exposure remains a security blocker before production use. Current consent-screen Testing/Production state and long-term token lifetime could not be independently inspected.

## Completed changes
https://github.com/James12ma/youtube-ai-engine/commit/30e89aa5305306785452d97ddd79758b9f3fca6e
- Fixed the existing channel-draft workflow's missing Pillow dependency; importing channel.thumbnail requires it.
- Removed unrelated Groq/Gemini/OpenRouter secrets from the OAuth workflow. Only YouTube credentials are loaded there now.
- Added an explicit rejection if a renderer QC backend ever returns passed=false. Existing run_qc already raises on actual failures; this is additional protection, not evidence that those failures previously bypassed its exception.
- Provider check stops after HTTP429 and accurately reports that later candidates were not sent; cooldowns are preserved.
- Added a manual bounded research-to-script dry run using the existing ContentPipeline, Router, StateStore and VerificationGate.

https://github.com/James12ma/youtube-ai-engine/commit/54cfaa1030cebfd7f2dea92f5487688cea8d1a8f
- Source retrieval reports safe, actionable failure categories without arbitrary response contents.
- No redirect, byte-limit, hostname or source-quality safeguard was relaxed.

https://github.com/James12ma/youtube-ai-engine/commit/54bcceaf865859b4d61482b094ec2be69928baf9
- Production renderer exports a plain SRT sidecar next to the MP4, using the original alignment blocks at millisecond precision.
- Rejects malformed/overlapping SRT intervals; retains readable ordered words without ASS karaoke styling.
- Production rendering and approval architecture preserved.
- Final source references are retrievable bounded NIST publication pages.

## Actual test results
Final full cloud CI:
https://github.com/James12ma/youtube-ai-engine/actions/runs/38680626425
Job 116244112023, executable revision 54bcceaf865859b4d61482b094ec2be69928baf9.
211 PASSED, 3 SKIPPED in 45.44 seconds. Compile and real Chromium recording tests PASS.
Skipped tests are the three API smoke tests deliberately lacking provider keys in offline CI.
The earlier intermediate CI on 30e89aa also passed 209 tests, 3 skipped:
https://github.com/James12ma/youtube-ai-engine/actions/runs/38680206251
Local focused regressions passed: 38 tests in 1.55 seconds (narration/SRT/OAuth/production boundaries).
Fixtures in the QC failure test inject narration/alignment; they are explicitly NOT real speech evidence.

## Live research and AI availability
Final research dry run:
https://github.com/James12ma/youtube-ai-engine/actions/runs/38680697179
Job 116244334545, executable revision 54bcceaf865859b4d61482b094ec2be69928baf9.
Successfully fetched the actual public publication pages:
- https://csrc.nist.gov/pubs/ir/7621/r1/final — 2144 extracted characters.
- https://csrc.nist.gov/pubs/sp/1300/final — 2841 extracted characters.
These snapshots are publication abstracts/metadata, NOT the full linked PDF guides. Both are NIST sources, not independent organizations.
The scenario is choosing a small-business cybersecurity baseline before workflow automation. No legal compliance guarantee is made.

Verified OpenRouter is_free_tier=true and every returned pricing field for the selected :free model is zero.
One actual generation request reached google/gemma-4-26b-a4b-it:free and returned HTTP429.
The pipeline stopped at research generation: pipeline_passed=false. No researched script, storyboard, entailment result or metadata draft was falsely marked complete. No paid failover occurred.
The workflow allows at most 20 generation requests (bounded lower when remaining quota is known), but sent only ONE in this execution.
The original production queue and durable production state were not changed; no schedule was enabled.

Separate provider check:
https://github.com/James12ma/youtube-ai-engine/actions/runs/38680463685
Groq and Gemini authenticate through read-only model listing, and configured model IDs exist. Their account-free billing state remains unverified, so generation is disabled.
OpenRouter authenticates as a free account; one verified-free generation request returned HTTP429. Remaining model candidates were not sent.
Two live free generation requests were attempted across these separate final checks. Neither succeeded. Repeated requests or paid routes were not used to bypass the limit.

## Narration, video, animation and delivery
Existing actual neural/media evidence remains valid; this execution did not pretend to generate a new researched long-form video:
- Real Piper + WhisperX CTC + responsive Playwright + FFmpeg, both formats PASS:
  https://github.com/James12ma/youtube-ai-engine/actions/runs/38672697309
- Real opt-in Edge fallback voice PASS:
  https://github.com/James12ma/youtube-ai-engine/actions/runs/38672901634

Delivered samples are the existing original functional expense-rule demo, 17.229 seconds each:
- Landscape 1920x1080, H.264 video + AAC 48 kHz audio.
- Portrait 1080x1920, H.264 video + AAC 48 kHz audio.
- Genuine Piper narration and 47 WhisperX-aligned ordered words; animated word highlighting, real responsive browser actions/focus and native portrait layout.
- Measured final loudness -16.49 LUFS and true peak -1.46 dBTP; prior technical QC and full independent FFmpeg decode passed.
- Original example inputs: travel 120 dollars requires manager review; lowering to 80 dollars produces automatic approval. These are demo inputs, not business-performance claims.
- Thumbnail is an actual generated 1280x720 JPEG using a genuine demo screenshot.
- Metadata remains a draft, with no invented owner synthetic-media decision.
This execution reconfirmed audio streams and exact MP4 hashes, and ran the NEW production SRT exporter on the actual downloaded WhisperX word files; all 47 words are retained.
Landscape MP4 SHA256: 51b8924bc15d2847f5a2f322cfd53fecd0eb5ca2756b84693121771daf452c7c
Portrait MP4 SHA256: f66fb12811bbd17ec3ae8912d0e87429d466eab585aaf3a79d6f9ffa809fffdf
Landscape is an aspect ratio, not proof of an 8–12 minute long-form video. That full source-generated long-form path is NOT live-validated.
No new human review, pronunciation approval, commercial voice/dataset rights clearance, monetization eligibility or copyright guarantee is claimed. Existing editorial and exact-release approval gates remain required.

## Final blockers and spending
1. Exposed credentials require secure rotation/cutover with Google Cloud account access; not completed here.
2. Live free AI generation is blocked by OpenRouter HTTP429. Groq/Gemini free-account billing verification remains unavailable.
3. A successful source-to-script dry run and owner-reviewed long-form production render are still required.
4. Final editorial/rights/synthetic-media disclosure decisions and explicit approval of the exact release remain outstanding.

No money spent or paid APIs/subscriptions activated by this execution. GitHub runs used the existing zero-cost confirmation gate and included resources; no spending settings were increased.
No YouTube video was uploaded (private, unlisted or public) or published.
No credential values were introduced into code, chat, logs, reports or artifacts by this work.
OAuth is operational for LogicScript. Full unattended production is not yet ready.
