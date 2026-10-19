# YouTube SEO Intelligence — read-only, owner controlled

An extension to the existing LogicScript and Alan7 engine. This DOES NOT replace the
current metadata generation, packaging quality, research gate, approval gate or renderer.

## Capabilities

- Official YouTube Data API v3 search by topic, preferred language and region.
- Public stats: video views, likes, comments and available channel subscriber counts.
- Extracts public video tags when YouTube supplies them.
- Drafts candidate titles only from the owner's topic and existing reviewed title.
- Observed competitor tags are clearly separated, never inserted into metadata.
- Writes seo_review.json and telegram_review.txt for owner approval. Never publishes.

US regionCode means *video availability in the US*, not the origin of viewers.
Language is a search preference, not a strict filter. Search results do not
measure keyword volume, future ranking, view growth, RPM or revenue.

## CLI for Alan7 and LogicScript

Offline mode, from an existing public-data snapshot:

    python -m channel.cli seo-review --topic "cybersecurity baseline" \
      --snapshot observations.json --region US --language en --out outputs/seo-1

Snapshot JSON includes videos and channels arrays. Videos have id, title,
channel_title, tags, view_count, like_count, comment_count and published_at.
Retain source provenance; never present fixtures as fresh live research.

Use an existing draft as source for the title and topic-only tags:

    python -m channel.cli seo-review --topic "cybersecurity baseline" \
      --draft outputs/drafts/existing-draft --snapshot observations.json \
      --out outputs/seo-2

Draft topic must match the report topic. No script or release file is modified.

Official live public lookup (explicit opt-in):

    export YOUTUBE_API_KEY="set-this-securely-outside-git"
    python -m channel.cli seo-review --topic "cybersecurity baseline" \
      --language en --region US --max-results 8 --live --out outputs/seo-3

Optional --video-url accepts a single YouTube video URL, and --channel-id
accepts an existing UC... channel ID, instead of topic search. Limits:
at most ten videos and three official API read requests per run. A standalone
YouTube Data API key is required; uploader OAuth is not automatically an API key.
Consult current quota information:
https://developers.google.com/youtube/data/determine_quota_cost

## Telegram: owner-only on-demand research

Once this branch is merged, deployed, and Cloudflare Worker secret
YOUTUBE_API_KEY is securely configured, send to the existing Alan7 bot:

    /seo es ballenas jorobadas
    /seo en cybersecurity for small businesses

Returns a compact, HTML-escaped, read-only public competitor report.
Without the configured secret it returns a setup warning.
It does NOT dispatch GitHub Actions jobs for SEO. No cost or activity when idle.
Maximum five public videos, three official API read requests per command.

IMPORTANT: This branch is not yet a live Cloudflare deployment. Do not put
API keys in Git, Telegram messages, chat transcripts, command lines or logs.

## Security and editorial boundaries

No SEOStudio scraping or bypass of automation restrictions; no paid API service
or subscriptions enabled; no automatic title replacement, uploads, publication
or metric manipulation. Competitor material is not verification of factual
script claims. Human approval and source checks remain mandatory.
Python tests use HTTPX MockTransport and JS tests replace fetch, so no external
requests occur during offline tests.


## SEO Editorial Package — second stage

Each existing CLI seo-review also generates an **unapproved** editorial proposal:
- seo_editorial_package.json — five title options, hook, provisional description,
  topic-derived keywords/tags and three hashtags;
- seo_editorial_telegram.txt — concise phone-review representation.

Choose mode explicitly if the language alone doesn't convey the content type:

    python -m channel.cli seo-review --topic "ballenas jorobadas" \
      --language es --mode documentary --snapshot observations.json --out outputs/seo-doc
    python -m channel.cli seo-review --topic "Excel expense tracker" \
      --language en --mode tutorial --snapshot observations.json --out outputs/seo-tutorial

The output remains a **deterministic, $0 template-based editorial draft, NOT an LLM
director**. It uses observed competitor title keywords as sampled themes with counts
(but DOES NOT claim they caused views, does not blindly copy competitors' brands,
does not scrape, and never modifies verified script or release metadata).
Descriptions intentionally contain placeholders for verified footage, claims, credits
and links. For a given verified draft, the original title and hook are preserved
for reference and are not overwritten.

Telegram: use the same existing owner-only Alan7 bot, which now supports:

    /seopack es documentary ballenas jorobadas
    /seopack en tutorial Excel expense tracker

The shortened alias doc is also accepted; default Spanish mode is documentary,
default English mode is tutorial. Each owner-requested run reads at most one
search and one video stats lookup from the official API. No scheduled searches,
GitHub Action dispatch, change to Telegram queue, publication, added subscriptions
or paid LLM calls. Owner must approve titles, hook, metadata and footage separately.
The main engine's source-backed metadata generator and YouTube upload digest gate
remain the only paths to approved release packaging.

Both CLI and Telegram paths are additionally covered by offline mock tests.

## Verified Script Director Bridge (v3)

The earlier seopack command only sees public competitor metadata. It cannot produce a verified script.

New owner-only on-demand Telegram preflight:

    /director en tutorial Excel expense tracker
    /director es doc ballenas jorobadas

It reports observed competitor title phrases with counts and an editorial production plan,
but clearly says no verified script, real capture, or footage was generated.

The existing source-backed research pipeline creates research.json, script.json,
storyboard.json, and verification_gate.json, using owner-approved HTTPS sources and
an explicitly authorized free provider. To connect these source-verified artifacts:

    python -m channel.cli director-review --draft outputs/drafts/existing-draft \
      --mode tutorial --seo-snapshot observations.json --out outputs/director-review-1

Choose documentary for Alan7; --seo-snapshot is optional. Files written:
director_review.json and telegram_review.txt.

This bundles the exact existing source-verified script sections and narration,
provenance hashes of all four source artifacts, the existing verified metadata
and source URLs, editorial candidate titles from its own section headings, and a
planned storyboard explicitly marked as not a real recording.

If source-verification or script/storyboard evidence is absent or inconsistent,
the Director fails closed. It does NOT synthesize factual narration from rivals,
replace the existing Router, start a video render or upload, or modify approved metadata.

End-to-end Telegram execution of a new verified script is a separate orchestration
step not yet implemented; it requires reviewed URLs, free-only provider authorization
and available quotas. No hidden paid model is used.

## Source-backed script creation from Telegram (explicit owner action only)

Existing /director en tutorial ... remains a read-only public SEO preflight.
To start an actual script job, the owner must approve two distinct HTTPS
research sources in the same private Telegram command:

    /director draft en tutorial Excel expense tracker | https://APPROVED_SOURCE_1 | https://APPROVED_SOURCE_2

For Alan7: /director draft es doc ballenas jorobadas | URL1 | URL2

This dispatches the existing free-only verified research -> script -> storyboard
pipeline through separate alan7-director-draft.yml (not the video renderer).
The branch adds explicit Spanish support to the existing ContentPipeline thresholds;
if providers or sources fail the pipeline fails closed and never invents a draft.

Workflow gates: ZERO_COST_ACTIONS_CONFIRMED=1,
FREE_PROVIDER_ACCOUNTS_CONFIRMED=1, at least one configured free-tier provider.
It does not fall back to billable accounts. GitHub runners, free-tier provider
quotas and availability must be validated separately; no live job is dispatched
by code merge or scheduled cron. Only the exact owner command authorizes a run.

Success stores the original research.json, verification_gate.json, script.json,
storyboard.json, director_review.json, all source artifact digests and
script_full_review.txt in a private GitHub Actions artifact. The script document
is also sent to the owner in Telegram when bot secrets are available. D1 tracks
job state. Script and storyboard are drafts, not confirmed real recordings.
Human approval of footage, full rendering and YouTube upload remains required.

No project is restarted, no auto-merge of owner edits, no old LogicScript modules
removed and no project-specific subscription or paid API turned on.
