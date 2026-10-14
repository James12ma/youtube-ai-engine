# Actual GitHub validation — 2026-10-14

Private repository: https://github.com/James12ma/youtube-ai-engine

The initial complete import contained all 125 locally verified source files.
Its tree SHA matched the local tested source exactly. Architecture and original
modules were preserved. Subsequent commits fixed runner environment context,
standalone narration dependency closure and optional CI dependencies.

## Successful runs

| Workflow | Actual result | Run |
|---|---|---|
| Full offline CI | 175 passed, 3 skipped; compilation and genuine Chromium recording passed | https://github.com/James12ma/youtube-ai-engine/actions/runs/38512211938 |
| Piper / WhisperX CPU neural smoke | Synthesis, real CTC alignment, captions, 1080p H.264/AAC, independent quality gates and artifact upload all passed | https://github.com/James12ma/youtube-ai-engine/actions/runs/38512309600 |

The neural run tested executable configuration commit
`6186e75b5191dee0420847e4c875beae6581dca6`:

- 10.449 seconds, 31 aligned words, four subtitle blocks.
- Transcript and aligned caption word coverage: 100%.
- Final loudness: −16.77 LUFS; true peak: −1.46 dBTP.
- CPU-only PyTorch and complete dependency checks passed.
- Downloaded artifact digest matched GitHub; independent local verification of
  the downloaded WAV, word JSON, ASS and MP4 also passed.

Failures are not hidden: two initial invalid-workflow entries had no runners
because job-level env referenced the runner context. The first dispatched neural
attempt installed its dependencies and model but failed before synthesis on a
missing direct Pydantic dependency. After correction, the next attempt passed.

## Cost and configuration

Before runs, GitHub Free showed 1,752 of 2,000 included minutes used and 0.1 of
0.5 GB included storage used. Existing Actions spending budget: $0, billable
usage blocked. No budget was raised, payment method added, or paid service enabled.
Large weights and pip caches are not stored as Actions caches; output artifacts
are approximately 1.6 MB with seven-day retention.

`ZERO_COST_ACTIONS_CONFIRMED=1` is configured for this verified account state.
`FREE_PROVIDER_ACCOUNTS_CONFIRMED` and `ENABLE_AUTOMATION` remain unset.
The queue remains disabled and no secrets were supplied to this repository.
Workflow tokens use explicit permissions: read-only for test/render workflows;
the opt-in draft workflow requires write access to persist its Git state.

GitHub states branch protections will not be enforced on this private repository
in the current account plan. No paid upgrade or public conversion was performed.

## Remaining blockers

- Provider keys and verified free-account settings are absent: live Groq,
  Gemini and OpenRouter calls remain untested. Model allowlists do not prove
  that an account cannot be billed.
- Google Cloud console showed “Site Unavailable” in this browser after one
  reload. No OAuth client or owner YouTube consent could be configured live.
  The local Desktop consent flow and token-write protections are implemented
  and tested; account consent is not simulated.
- No always-on worker is deployed. Manual GitHub CPU workflows are operational.
- Human listening, commercial terms, source choices and editorial review remain
  owner tasks. No demo has owner release approval; no YouTube upload occurred.
