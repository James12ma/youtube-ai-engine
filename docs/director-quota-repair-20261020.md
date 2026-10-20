# Director draft quota repair — 2026-10-20

Base: 989a4060ae6878f3bb926abad0c8c6e22d98d681.
Investigated run: https://github.com/James12ma/youtube-ai-engine/actions/runs/39337749774
Historical runtime: 695ce33e196f9b7bb52d3a13f971ad9ed636784c.

## Corrected behavior

- Source-backed draft generation enables at most 65 seconds of local minute-quota waiting per router task. Other router callers retain the existing no-wait default.
- Approved, available fallback providers run before waiting. Reservations still happen before HTTP dispatch; daily limits, authentication cooldowns, circuit breakers, model allowlists and leases remain enforced.
- The observed 18 reserved attempts plus a 3-attempt request under a 20/minute cap waits for the rolling window to reopen instead of immediately failing.
- Each successful HTTP adapter response reports its actual attempt count. The router refunds only provably unused retries, idempotently. Unknown outcomes, failures, interrupted calls and legacy adapters retain their full reservation. A successful first attempt therefore consumes one request rather than three.
- Non-authentication ClientError responses no longer impose a 24-hour authentication cooldown. They still count toward the circuit breaker. AuthError retains the 24-hour cooldown.
- Director review failures now produce labeled failure evidence. Missing artifact files produce an error rather than a green storage step with no artifact.
- Script duration, citations, source verification, storyboard and Director acceptance gates are unchanged. No render/upload authorization is granted.

## Executed validation

`python -m pytest -q -rs --junitxml=/tmp/director-quota-validation.xml`

Result: **417 passed, 4 skipped**, 29.05 seconds, no failures.
Skips: espeak unavailable; three live-provider smoke tests have no local API keys.
Chromium was installed locally to run both real recording tests successfully.

`git diff --check` and compilation of changed Python modules passed.

Regression coverage includes the observed 18+3 quota failure, bounded waiting, available fallback precedence, daily exhaustion, actual HTTP success accounting, idempotent refunds, invalid/unknown attempt counts, separate client/auth handling, and failure evidence after Director rejection.

## Remaining live acceptance

A new owner-requested Director run must use this branch's new commit, not rerun the old SHA. The connected GitHub tools expose reads and reruns but no workflow-dispatch operation. Local execution cannot use repository Actions secrets. No new live provider request, Telegram delivery, render or upload was performed during this repair.

After supported dispatch is available, run `.github/workflows/alan7-director-draft.yml` on `fix/director-quota-pacing-20261020`, job ID `d20c0001`, with this payload:

```json
{"language":"en","mode":"tutorial","topic":"Excel expense tracker","urls":["https://support.microsoft.com/en-us/excel/get-started/create-and-format-tables?utm_source=chatgpt.com","https://support.microsoft.com/en-us/excel/create-a-simple-formula?utm_source=chatgpt.com"]}
```

The workflow retains its existing free-account and free-Actions preflight. If authentication errors or the actual daily allowance block the run, retain the labeled evidence and report the blocker; do not reset controls or substitute unverified content.

Acceptance requires a successful draft step, a real artifact containing the source-backed script, storyboard, final verification report and Director review, and confirmation of the owner-review document delivery. An unverified candidate alone is not success.
