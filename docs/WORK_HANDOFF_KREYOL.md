# Autonomous YouTube AI Engine — Master Code Handoff (Tasks 1–8 + Release)

## Sa pake a gen ladan

- Tasks 1–3: Git-backed state, Groq/Gemini/OpenRouter rate limits, failover, safety.
- Tasks 4–5: source-backed script, factual and citation verification, editorial gate.
- Tasks 6–7: FFmpeg/video, original explanatory cards and REAL local Playwright demo.
- Task 8: Piper CPU voice + WhisperX REAL forced alignment, GitHub Actions smoke test.
- `channel/`: assembled CLI to create drafts, render approved narration/script, generate SEO,
  draw original thumbnails, build immutable release checksums, demand owner approval,
  upload to YouTube (private by default), optional queue and opt-in scheduled drafts.
- `.github/workflows/channel-ci.yml`: manual/PR offline tests.
- `.github/workflows/channel-draft.yml`: workflow dispatch or opt-in 3/day source-curated
  script drafts. No automated upload. Setting `ENABLE_AUTOMATION=1` is owner action.
- `.github/workflows/narration-smoke.yml`: optional manual neural voice validation.

## What Work must do in deployment (not optional)

1. Create a new private GitHub repository, import this source tree, preserve original code.
2. Run `python -m compileall -q` and `python -m pytest -q` with dependencies.
3. Read the existing audit reports and resolve any CI/environment regressions.
4. Verify GitHub Actions minute limits and billing settings. Hard budget $0. Do not enable a paid plan.
5. Add *ONLY owner-approved* source URLs to `topic_queue.json`; the supplied queue is disabled.
6. Verify OpenRouter `:free` and Groq/Gemini account free tier and billing rules.
   Do not set `ROUTER_ALLOW_LIVE_API=1` until the owner approves limited free calls.
7. Run the manual Piper + WhisperX smoke workflow exactly once if allowed within free quota;
   download WAV, forced-word JSON, ASS, MP4, QC artifacts. Listen and inspect captions.
8. Configure YouTube OAuth (`youtube.upload` scope) through owner interaction; tokens must
   NEVER be committed, printed, or put in uploaded artifacts.
9. Run a full E2E dry run (research→verification→script→real assets→neural render→metadata→
   thumbnail→editorial review). Verify quality manually before release.
10. For a private test upload, demand explicit owner confirmation and exact release digest.
    Never enable public/unlisted uploads without separate owner approval.
11. Report what was actually executed and succeeded; no invented completion percentages.

## Source-only quality and safety constraints

No face required. Avoid invented benchmarks, charts, social proof or fake UI. The software
recordings should be real and screenshots legitimately obtained. Require human editorial
review for copyright, accuracy, pronunciation, AV sync and factual traces. YouTube's
inauthentic/mass-produced content policy makes templated videos a monetization risk.

## CLI

```bash
python -m channel.cli --help
python -m channel.cli thumbnail --text "Review Your Workflow" --out outputs/thumbnail.jpg
# After Work configures a Git remote, approved source queue, and free API keys:
python -m channel.cli next-draft --queue topic_queue.json --repo . --out-root outputs/drafts --allow-free-live-api
# Review the draft script, storyboard, claims, and license of recorded footage.
python -m channel.cli render --draft outputs/drafts/ENTRY --voice-model voices/en_US-libritts-high.onnx --out outputs/final.mp4 --reviewed
# For screen-recording/chart/broll scenes, pass --asset-map assets.json: {"0":"assets/real_recording.webm"}
# Create editorial_review.json only after independent checks: 
# {"gate_passed":true,"human_reviewed":true,"quality_passed":true,"reviewed_by":"owner"}
python -m channel.cli package --draft outputs/drafts/ENTRY --video outputs/final.mp4 --thumbnail outputs/thumbnail.jpg --editorial-report outputs/editorial_review.json --out outputs/release-001
# Read output manifest's `release_digest`, manually confirm it:
python -m channel.cli approve --release outputs/release-001 --digest EXACT_SHA256 --human-confirmed
# External YouTube upload stays BLOCKED unless independent secrets/gates are approved.
```

## GitHub deployment and scheduling

- CI test workflow automatically checks pull requests; the source queue job runs on manual
  dispatch, or 3 times a day ONLY IF the owner sets `ENABLE_AUTOMATION=1`.
- This schedules **drafts**, never publishing. Production video rendering is CPU-intensive
  and can exceed included Actions quota; Work must find a confirmed cost-free environment.
- GPU and paid image APIs are not required for offline prototypes. Real provider/API use
  and download resources must be validated within the account's quota.
- Google OAuth needs a user approval flow; user controls it, not the bot.

## Code-ready vs live-ready

The code is packaged and tests can run locally, but PRODUCTION IS NOT VALIDATED until Work
has connected free API keys, Piper and WhisperX models, YouTube OAuth and created an
owner-reviewed real video. This is not a guarantee of profit, monetization or free hosting.

## Primary source references

- https://developers.google.com/youtube/v3/docs/videos/insert
- https://developers.google.com/youtube/v3/docs/thumbnails/set
- https://support.google.com/youtube/answer/1311392
- https://support.google.com/youtube/answer/14328491
- https://docs.github.com/en/actions/concepts/security/secrets
