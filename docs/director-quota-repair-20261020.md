# Director draft repair — verified 2026-10-20

## Result

The existing source-backed Director workflow completed successfully on code commit `ea11d6d92233ae5de8f0b835d33c19504ac5a6e9`:

- Run: https://github.com/James12ma/youtube-ai-engine/actions/runs/39375623524
- Job: `d20c0007`, topic `Excel expense tracker`, English tutorial, same two Microsoft sources as the original failed request.
- Script: **1,508 narration words**, estimated **603.2 seconds**, **9 sections**.
- Storyboard: **12 scenes**.
- Final verification report: **4 accepted source claims, 0 rejected**.
- Director status: `OWNER_REVIEW_REQUIRED`.
- Artifact: `alan7-director-d20c0007`, ID `12242713015`, 11 files, 23,280-byte ZIP.
- ZIP SHA256: `ad470dfbcc34b8de045c7620ac4cfaaaea8aaf609509cec5a296ca4ef6055b56`.
- The ZIP was downloaded, its digest matched the Actions digest, and script, storyboard, verification and Director outputs were inspected.
- The workflow's Telegram document step completed without missing-secret or delivery-failure warnings. Its script reports a warning for every HTTP status other than 200; the accepted result is the owner-review document, not publication approval.

No video was rendered or uploaded. Editorial approval, render approval and actual screen-capture verification remain false. Source-claim checks do not replace human review of the whole narration or real screen footage.

## Changes

The original run 39337749774 rejected a 595-word script, then failed while repairing it because all providers were unavailable under the router's controls. Groq/Gemini had legacy auth/client-conflated cooldowns; OpenRouter could not reserve three attempts with 18 reserved under its 20/minute cap.

- Source-backed drafts can wait up to 65 seconds per task for local minute capacity. An available approved fallback runs before waiting. Daily limits, leases, free-model allowlists and actual authentication cooldowns remain enforced.
- Successful HTTP responses report their actual attempts. Unused retries are refunded once, only when proven; unknown/interrupted/failed outcomes stay fully reserved.
- Actual auth failures retain their cooldown. Client/schema failures are distinguished from provider outages; native invalid-JSON responses receive bounded correction retries. Blocked fallback providers no longer hide the preceding real error.
- Rate-limit pauses follow Retry-After or the existing fallback cooldown instead of an unrelated hour-long outage pause.
- The final numeric repair round rebuilds only from verified facts instead of copying the rejected paragraph. A response schema checks for unsupported numeric material before the unchanged production quality gates.
- Director-review errors now produce labeled failure evidence. Empty artifact uploads fail visibly.
- Director-only provider configuration uses documented Groq strict JSON Schema output and the reviewed free-tier Gemini replacement `gemini-3.1-flash-lite`. Other workflows keep their existing defaults. OpenRouter's Director override is `google/gemma-4-26b-a4b-it:free`.
- Quota diagnosis supports metadata-only GET requests and safe provider/model status reporting, with no generation requests or exposed credentials.

## Validation

- Local complete suite: **430 passed, 4 skipped**, 32.00 seconds, zero failures/errors.
- GitHub complete suite at the tested code commit: **431 passed, 3 skipped**, 56.76 seconds; run 39375549805. Its real lesson boundary check passed **15 Chromium tests**.
- The separate Router and SEO workflows passed as well.
- Local skips: espeak missing and three direct live-key smoke tests. GitHub has espeak; only the three direct live-key smoke tests skipped. The real Director integration above ran separately with Actions secrets.
- Changed modules compile; `git diff --check` passed.

Regression coverage includes the observed 18+3 failure, bounded waiting, fallback precedence, daily exhaustion, idempotent actual-attempt settlement, unknown outcomes, separate auth/client/schema handling, native JSON failures, safe error reporting, Director failure artifacts, numeric regeneration, recursive Groq schema conversion, and GET-only diagnostics.

## Live observations and bounded recovery

| Evidence | Observation |
| --- | --- |
| 39373066659 | Advanced beyond the original reservation failure; correctly rejected an unsupported numeric statement. Real failure evidence archived. |
| 39373571334 | The previous code-focused free model failed the bounded numeric repair schema. No output promoted. |
| 39374007222 / 39374487855 | The two tested OpenRouter Gemma models returned HTTP 429. These limits were not treated as successful drafts. |
| 39374233833 / 39374726093 | Read-only account diagnosis: confirmed free account, 12 of 50 daily requests used, 38 remaining. Groq/Gemini metadata authenticated with HTTP 200 and configured model presence. |
| 39374916774 / 39375284184 | Exposed client request failures, including Groq JSON-format rejection and Gemini 2.5 generation HTTP 404. |
| 39375623524 | Entire Director workflow succeeded, including final artifact and owner document delivery step. |

Targeted state recoveries are auditable on `router-state`: `5713a2339a142d1cdfddefbf9a30a4f9d42f43a1` (known schema-only false outage pause), `13933eb9ca02f193057009ba1bc21e2df28f38ea` (align known rate-limit pause with recorded provider cooldown), `b2bbadead85b3e836bace0d926266d1c22e30553` (revalidate two legacy auth/client-conflated cooldowns after current authenticated metadata checks), and `00d43b3cd757a71b64d0f26e18bf3aa08230e6af` (known client-only false outage pause).

No quota counter/window was reset. Existing provider circuits and real rate-limit controls were retained. Future actual auth failures still reinstate their cooldowns.

The successful run still recorded a Groq rejection of the numeric-repair schema; the verified fallback path completed the job. This is not a claim that every provider is healthy or that free capacity is unlimited.

## Primary compatibility references checked 2026-10-20

- https://console.groq.com/docs/structured-outputs — GPT-OSS strict JSON Schema support and required-field/closed-object rules.
- https://ai.google.dev/gemini-api/docs/pricing — free-tier input/output for Gemini 3.1 Flash-Lite; no paid tier or grounding was enabled.
- https://ai.google.dev/gemini-api/docs/openai — compatibility endpoint and request options.
- https://openrouter.ai/api/v1/models — the reviewed Gemma `:free` model IDs had zero prompt/completion prices and advertised JSON response-format support.
