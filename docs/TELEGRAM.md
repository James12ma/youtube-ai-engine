# LogicScript Telegram private review

This is a small transport for the existing engine, not a replacement pipeline.
It can send the existing verified video to the owner and answer private review
commands. It cannot upload to YouTube, approve a release, change credentials,
run shell commands, trigger paid generation, or post community comments.

## Configuration and owner-only activation

The October 15 audit found no Telegram secrets in this repository. No live
Telegram request or delivery has been verified yet.

1. In Telegram, open the official **@BotFather**, create a dedicated LogicScript
   bot with `/newbot` (or select your existing dedicated bot), and keep its token
   out of chat/screenshots. Do not select an unrelated business bot.
2. Add `TELEGRAM_BOT_TOKEN` directly in the repository's GitHub Actions Secrets
   form. Add `TELEGRAM_OWNER_ID` as a second secret containing your own positive
   numeric Telegram user ID. A private user chat ID equals that user ID; do not
   use a group/channel ID. Verify the identity rather than trusting the first
   person who starts the bot. GitHub keeps the secret values unreadable afterward.
3. Open your bot in Telegram and tap **Start**. Telegram will not allow a bot to
   initiate a new private conversation with a user who has never started it.
4. Run **LogicScript Telegram (private review only)**, default mode `verify`.
   This calls `getMe` only; it does not send a message or test YouTube OAuth.
   Then mode `deliver` sends the exact SHA-256-verified final review MP4.

The developer can run these workflow steps once secure configuration exists.
No credentials should be supplied to an assistant through a chat message.

## Commands and lifecycle

- `/help` and `/start`: explain available commands and limits.
- `/status`: pinned review package status, explicitly not a live OAuth check.
- `/video`: send the verified 6m47s 1080p review video as playable MPEG4.
- `/files`: thumbnail, SRT, script, sources, and the standalone practice lab.

`listen` runs for **five minutes**, manually started, with no cron or looping
workflow. Only original private messages from the preconfigured owner are
accepted. Group, forwarded, edited, bot, and callback messages are ignored.
Commands sent before a session starts are intentionally discarded, avoiding
replay after runner restarts. Unknown commands, including `/approve` or
`/publish`, only display help and never change the release approval state.
The existing exact-digest approval and independent YouTube upload gates remain
in force.

This is **not an always-on deployment**. GitHub Free private-repository included
minutes are finite and shared across projects. Running a poller continuously
would exceed the owner's $0 budget. A 24/7 webhook host requires a separate
verified zero-cost hosting configuration; none is provisioned or billed here.
Each manual workflow uses included runner minutes, so stop before allowance is
exhausted. `ZERO_COST_ACTIONS_CONFIRMED=1` remains required.

The poller checks `getWebhookInfo` and refuses to run if a webhook is installed.
It never deletes a webhook or changes another bot's deployment. Use one polling
process only. GitHub workflow concurrency prevents overlapping workflow sessions.

## Artifact and security constraints

The workflow fetches `lesson-polished` from render run **38721241174** and checks
all six fixed file hashes before delivery. It uses Actions read permission, not
a personal access token. GitHub artifacts expire after seven days (approximately
October 22, 2026); after expiry a verified restored artifact or a fresh render
must be deliberately pinned. Missing, oversized, symlink-escaped, or changed
files are refused. The currently verified MP4 is 28,950,452 bytes, below the
conservative 49 MB transfer cap.

No YouTube or AI-provider secrets are passed to the bot job. API responses and
httpx exception URLs are never printed. Outgoing media are not retried blindly,
since a lost response can follow a successful transfer. A failed send requires
checking the private chat before another manual delivery.

## Verification

Twenty local mocked-transport regression cases passed on October 15, 2026,
covering owner binding, group/forward/callback rejection, no approval execution,
webhook preservation, token-safe errors, hash checks, actual multipart transfer,
backlog handling, and session bounds. The six actual render files also matched
the configured hashes locally. These tests do not prove live Telegram delivery;
that requires the real token, owner binding, and a successful workflow run.

Telegram API reference: https://core.telegram.org/bots/api

## Live GitHub attempt and current blocker (2026-10-15 18:27 UTC)

Commit `17009ac5747f03e1ede2093d74ac4529e65284f5` was committed to existing
`main`. The actual existing full CI was manually dispatched as run
`38785675624` (#16). **The job did not start.** GitHub's annotation says recent
account payments failed or the spending limit must be increased. A read-only
billing inspection resolved the ambiguity: **2,000 / 2,000 included Actions
minutes used**, $0 billable Actions usage, reset in 17 days. The $12.03 gross
metered figure was fully covered by $12.03 included discounts; it is not a bill.

No spending limit was increased, payment added, or paid runner enabled. No
retry is scheduled. The previous 233-pass CI remains historical; the new bot
has 20 passing local tests, not a passing live full-CI result. Bot activation
currently needs both secure Telegram configuration and restored included
Actions capacity or a separately verified $0 host. Do not instruct the owner
to pay or make their private repository public to work around this limit.
