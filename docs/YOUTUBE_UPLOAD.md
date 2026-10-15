# Direct YouTube upload — owner-approved, private first

Workflow: `.github/workflows/youtube-upload.yml` (manual dispatch only). It uploads one
approved release package and **never publishes publicly**: the choices are `private`
(default) or `unlisted`. Switching a checked video to Public is done by the owner in YouTube Studio.

## Flow

1. **Candidate** (offline, no approval):
   `python -m scripts.lesson_release candidate --artifact <lesson-polished> --lesson content/expense-rule-lesson --out out/candidate --topic "..." --thumbnail-text "..."`
   Produces video, thumbnail, SRT, metadata, description, chapters, tags and `quality_report.json`.
2. **Owner review**: watch the full video; decide the title and the altered/synthetic-content disclosure.
3. **Finalize** (offline, only after approval of the exact video SHA-256):
   `python -m scripts.lesson_release finalize --candidate out/candidate --out out/release --approval "<statement>" --synthetic-media yes|no --video-sha256 <sha> --zip out/release.zip`
   Prints the `release_digest`.
4. **Store**: attach `release.zip` to a private GitHub Release (e.g. tag `lesson-001-rc1`). Assets of a private repository's releases are private.
5. **Upload**: Actions → "YouTube upload" → Run workflow with the tag, the exact digest, `private`, and the "I watched and approve" box.

## Safety gates (all must hold)

| Gate | Where |
|---|---|
| Repository variables `ZERO_COST_ACTIONS_CONFIRMED=1` and `YOUTUBE_UPLOAD_ALLOWED=1` | job `if` |
| "I watched this exact video and approve" ticked | job `if` |
| Typed digest equals the package's hash-derived digest | `channel.cli approve` and the uploader |
| Every hashed file unchanged (video, thumbnail, SRT, metadata, quality report, editorial review) | manifest verification |
| OAuth refresh works **and** the channel equals `YOUTUBE_EXPECTED_CHANNEL_ID` | `scripts.check_cloud_oauth` before upload |
| No receipt already attached to the Release | duplicate guard before upload |
| Owner's synthetic-media decision recorded | uploader refuses otherwise |

Inputs reach the shell only through environment variables and are validated by regex.
Credentials are never echoed; the job uploads no artifacts; checkout does not persist the token.

## Uploader behaviour

- Resumable upload; only HTTP 500/502/503/504 and connection errors are retried (max 5, exponential backoff).
  Client errors fail closed without a receipt; error messages contain the HTTP status only.
- The receipt is written **immediately** after YouTube returns the video ID, then the thumbnail is set.
  A thumbnail failure is reported in the receipt (set it in Studio) and can never cause a second upload.
- Captions are **not** uploaded by default: the captions API needs the broader `youtube.force-ssl` scope.
  Upload `captions.srt` in Studio (Subtitles → Add → Upload file), or opt in with `--upload-captions` after granting that scope.

## Known platform caveats

- Google's API documentation currently contains conflicting statements about whether uploads from
  unaudited API projects are restricted to private viewing. Upload privately first; if Studio shows
  the video as locked private, the project needs YouTube's API compliance audit or a manual Studio upload.
- Custom thumbnails require a channel with verified features (phone verification) in YouTube Studio.
- If the Google OAuth consent screen is in "Testing", refresh tokens expire after 7 days.
- Each run uses GitHub Actions minutes; with the free allowance exhausted, runs will not start.
