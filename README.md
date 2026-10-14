# Autonomous YouTube AI Engine — Consolidated Source Handoff

**Purpose:** One source package for ChatGPT Work to import into a private GitHub repository, test, wire up and run. This is an integrated **development release candidate**, NOT a live or monetized YouTube channel.

**Status of this exact consolidated package:** On this machine, `python -m compileall` succeeded; `python -m pytest -q` returned **170 passed, 3 skipped**. No paid API calls, no real neural voice or YouTube uploads were executed in this packaging session.

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
