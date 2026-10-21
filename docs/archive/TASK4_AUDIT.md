# Router V3.1 — Task 4 content pipeline audit

## Test environment and actual results

- Python 3.13.5; Git 2.47.3; offline `pytest` using mock providers and a local Git repository.
- Initial reconstructed DeepSeek Task 4 cases: **8 passed** (with the prior Task 1–3 corrected code).
- Full suite before adversarial tests: **72 passed, 3 skipped**.
- Added adversarial tests: seven initial failures against the original Task 4 proposal (misstated statistic, unchecked duration, overlapping scenes, uncited numeric hook, private HTTPS host, redirect, script-tag content).
- After revisions and additional tests: **84 passed, 3 skipped**.
- Three live-provider smoke tests were intentionally skipped; no paid API request was made.
- Files in this package were reconstructed from the Task 4 text and extended with targeted corrections; the original Task 4 had not been supplied as an attached repository.

## Critical repairs

1. Claim excerpts must match the fetched source and numerical claims cannot introduce numbers absent from that source (basic consistency only).
2. Default English long-form script duration is checked against 8–12 minutes (480–720 seconds), based on word count / configured speaking speed. This is not a substitute for actual voiceover timing.
3. Storyboards must have sequential scene indices, finite times, and contiguous non-overlapping scene ranges.
4. The research cache is keyed by a digest of fetched source contents (not URL alone); script and storyboard cache keys incorporate their actual inputs and quality settings.
5. Fetching requires an explicit HTTPS hostname allowlist. It rejects URLs with credentials, nonstandard ports, IP-literal hosts, redirect chains, unsupported media and oversized responses. HTML script/style/nav elements are ignored. DNS rebinding and compromised allowlisted domains remain network-security concerns; restrict outbound network access in production.
6. Numerical statements are rejected in hooks/CTAs because current schemas provide no citation references for them. Narration with numerals requires claim IDs.
7. Quality failures generate up to two revised provider prompts by default; bad first responses no longer permanently poison retries via the Router's content-addressed cache.
8. The stored verification artifact explicitly says its evidence level is `excerpt_and_numeric_consistency_only` and `ready_for_publication` is always false. Script artifacts require editorial review.

## Important unresolved limitations

- **Not full semantic fact verification:** excerpt matching plus number consistency cannot prove that a paraphrase is true. A source might be false or a sentence might reverse causality. Secondary claim-entailment verification, cross-source corroboration, and source authority checks are required.
- Repeating the same numeric value in an unrelated source paragraph can pass the numeric consistency check.
- The prototype requires supplied `seed_urls`; it does not discover or rank trustworthy sources.
- `HttpSourceFetcher` is safe only as part of a restricted, carefully allowlisted setup. DNS rebinding risk cannot be completely ruled out by string checks alone.
- HTML text extraction is basic; no PDF/JS-rendered documentation support. Obey source terms and avoid publishing extensive copyrighted extracts.
- The Stage 1 restart path currently re-fetches sources; network outages can block recovery even if an old artifact exists.
- Source and claim snapshots are committed to Git state and the earlier `StateStore` has a finite size cap. Long-term storage/retention needs redesign.
- Actual Google/Groq/OpenRouter authentication, Github Actions production behavior, and externally sourced outputs have not been tested.
- No TTS, animation, real video recording, thumbnail generation, upload or publication was added.

## Commands

```bash
python -m pip install -r requirements.txt -r requirements-dev.txt
python -m compileall -q state_store.py adapters router pipeline tests
pytest -q
pytest -q tests/test_pipeline_offline.py tests/test_pipeline_audit.py -v
```

To use the real `HttpSourceFetcher`, initialize it with a list of trusted hosts, such as:

```python
from pipeline import HttpSourceFetcher
fetcher = HttpSourceFetcher(allowed_hosts={"developers.google.com", "support.google.com"})
```

Do not use the provided mock tests as evidence that a live research/video system is operating.
