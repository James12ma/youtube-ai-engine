# Autonomous YouTube AI Engine — Consolidated Source Handoff

**Purpose:** One source package for ChatGPT Work to import into a private GitHub repository, test, wire up and run. This is an integrated **development release candidate**, NOT a live or monetized YouTube channel.

**Verified status (2026-10-14):** The private repository is created and the complete source imported. Remote GitHub CI passed with **178 passed, 3 skipped** (live provider keys absent). The real CPU Piper 1.8.0 / WhisperX 3.8.6 smoke passed on GitHub, including independent word-caption and 1080p media gates. The animated action-paced cloud render also passed for native 1920×1080 and 1080×1920 outputs (15.5 seconds each, 47 aligned words, 100% word coverage). Local real browser/neural and assembled channel renderer demos also passed. Live provider generation, Google consent and YouTube upload remain pending. No paid API calls or YouTube uploads occurred. See `docs/GITHUB_VERIFICATION.md` for run links and `docs/OPERATIONS_VERIFIED.md` for reproduction.

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
