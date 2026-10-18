# Alan7 Telegram -> YouTube AI Engine (video requests)

This is a **draft connection**, not a live production rollout.

## Phone commands (after code is reviewed, merged and deployed)

```text
/topics
/video 5 types of job interviews | lang=en | duration=60 | style=motion | mode=preview
/video 5 types of job interviews | lang=en | duration=60 | style=motion | mode=full
/video Ce qui se passe en France | lang=fr | duration=60 | style=news
/queue
/status
```

- Owner-only private Telegram commands use the existing Cloudflare Worker and D1 job queue.
- The code accepts multiple subject requests; **only registered `job-interviews` in English for 60 seconds with `style=motion` is currently renderable.** Preview = four seconds, full = sixty seconds.
- Unregistered subjects such as France news, wildlife, and arbitrary tutorials are saved in D1 as *awaiting director*. They are **not** sent to a renderer, and the bot explicitly says no video was made.
- The current director is a **deterministic safety router, not Gemini**. Gemini is a candidate future model. No Gemini key, free tier, or end-to-end Gemini generation has been configured or tested.
- When a supported request is authorized for the no-cost runner, the bot dispatches `.github/workflows/alan7-video.yml`, which executes `python -m tiktok_motion.produce`, does technical QC and sends the MP4 back in the owner's private Telegram chat.
- YouTube, TikTok and all other public posting remain disabled. There is no auto-approval.

## Cost/availability gate

The user's GitHub Actions free minutes were previously exhausted. The bot therefore **does not launch new render workflows by default**. A job remains in `awaiting_approval` if `VIDEO_RUNNER_ENABLED` is not `1` or a GitHub token is missing.

Activating the free runner requires BOTH:
1. Verifying that a no-cost GitHub Actions quota is actually available and setting repository variable `ZERO_COST_ACTIONS_CONFIRMED=1`.
2. Explicit owner permission to set the Cloudflare Worker environment variable `VIDEO_RUNNER_ENABLED=1` and a valid GitHub token, *after* the render workflow is on the repository's default branch.

The workflow has its own fail-closed guard for `ZERO_COST_ACTIONS_CONFIRMED`. Do **not** activate either switch or change billing settings without owner approval.

Existing owner-only authentication and the existing Telegram webhook secret are preserved.

## Testing

Pure routing tests: `node --test alan7_bot/test/video-director.test.mjs`.

Miniflare end-to-end Worker tests: `cd alan7_bot && npm ci && npm test`.

Deployment via the existing Cloudflare workflow requires **free GitHub Actions runner minutes**. The new workflow is dispatched against `main`, as required by GitHub's workflow dispatch. Because this is a draft branch, it **does not run on the deployed bot yet**.

This patch does not modify Alan7 documentary production, LogicScript, or the ongoing Claude premium render. It should not be merged automatically while that work is active.
