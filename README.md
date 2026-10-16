# Autonomous YouTube AI Engine — Consolidated Source Handoff

**Purpose:** One source package for ChatGPT Work to import into a private GitHub repository, test, wire up and run. This is an integrated **development release candidate**, NOT a live or monetized YouTube channel.

**Verified status (2026-10-15):** Final regression passed **233 tests; 3 live API tests skipped** on commit `8fdc42a`. The corrected **6m47s English tutorial** passed actual cloud rendering, independent MP4 decode/audio/caption checks and a separate visual review; its offline practice lab is reproducible in Chromium. Fresh OAuth refresh and read-only access to **LogicScript** passed with the expected channel ID. **Production remains gated:** exposed credentials still require secure rotation (Google Cloud is inaccessible in the current browser), the final adaptive script-budget correction has not passed a fresh live E2E run (latest live script was correctly rejected at 1,045/1,200 required words), and owner listening/editorial approval is absent. No paid service, YouTube upload or publication was performed. See [the current publication review](docs/FIRST_VIDEO_PUBLICATION_REVIEW_2026-10-15.md) for exact run links, fixes, limitations and MP4 checksum.

**Update (2026-10-16):** the automated research → script → storyboard → verification pipeline passed live for the first time (1,458-word script, 5/5 claims verified, $0). Repository is public so GitHub Actions runs at no cost. See [docs/LIVE_PIPELINE_PASS_2026-10-16.md](docs/LIVE_PIPELINE_PASS_2026-10-16.md).

## Start here

- **`docs/WORK_HANDOFF_KREYOL.md`** — deployment sequence and safety constraints.
- **`docs/WORK_MASTER_PROMPT_ENGLISH.txt`** — full ChatGPT Work execution instruction.
- **`channel/`** — unified CLI: draft, next-draft, render, thumbnail, package, approve, upload, check.
- **`topic_queue.json`** — example disabled; Work must add REAL approved source URLs.
- **`.github/workflows/`** — CI, manual narration smoke, owner initiated / opt-in scheduled drafts.
- **`TASK*_AUDIT.md`** — limitations of past engineering versions.

## No-cost and security

All publishing is disabled unless the owner explicitly approves the exact release digest. Even a private upload requires separate environment gates. Public uploads require an additional gate. Google OAuth files and provider keys must NEVER go into Git history or release artifacts. Routine GitHub scheduled drafts are **disabled** until the owner sets `ENABLE_AUTOMATION=1` and checks billing/allowances.

## Tests

```bash
python -m compileall -q state_store.py adapters router pipeline verification production production_pro narration_pro channel scripts tests
python -m pytest -q
python -m channel.cli --help
```

Full video production requires CPU Piper and WhisperX model downloads, FFmpeg, accurate footage/assets, a review-approved script, and a cost-free runtime with adequate CPU/RAM. A passing unit suite is **not** proof of production readiness or commercial/monetization quality.
