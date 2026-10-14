# Router V3 — Task 5 Audit (2026-10-13)

## Scope
This package is the prior locally tested Tasks 1–4 implementation plus a new `verification/` package and offline tests. No real provider API calls, payments or YouTube uploads occurred. Task 4 and prior modules were not rewritten.

## Results
- `python -m compileall -q state_store.py adapters router pipeline verification tests`: exit code 0
- `pytest -q --disable-warnings`: 126 passed, 3 skipped (in local runtime, Python 3.13.5)
- Task 5 tests: 42 passed, includes integrated Task 1 + Task 3 + Task 4 + Task 5 test with mocked adapters.
- 3 provider smoke tests were skipped deliberately. No live OAuth, Google API, or paid requests were executed.

## Original Task 5 design defects identified by static review
1. A script's citation could point to a rejected claim and still pass if any other claim was accepted.
2. Entailment responses did not ensure exactly one matching judgment per requested claim/source and could accept foreign source IDs.
3. The contradiction detector could silently skip unrelated-word pairs and extra groups.
4. Domain tier alone is not evidence of the article's reliability or claims' truth. The original string-match heuristics could misclassify spoofed hostnames.
5. Source content was not included in Task 5's entailment cache key, permitting stale verdict reuse after sources changed.
6. Corroboration bonus was awarded for duplicate or non-independent source origins.
7. Original Task 5 added a passive gate but did not wire it into the pipeline.
8. Numeric source-to-claim and cited-narration consistency were not rechecked at this final gate.

## Corrective design
- Fail closed on missing/foreign/duplicate entailment judgments and inconsistent artifact provenance.
- Versioned SHA-256 of source contents and snippets in router inputs.
- Check every unordered claim pair (bounded; fail closed above resource cap). No silent skipping.
- Restrict correlation bonus to distinct recognized domain origins, noting this still cannot prove independence.
- Compare numerical values in claim/source and narrator/cited claims, including common number words; block unsupported numbers in hook/CTA.
- Build traces only from verdict-accepted sources and reject citations to rejected claims.
- Supply `VerifiedContentPipeline` facade that forces the gate after content generation while keeping publication authorization always false.

## Unresolved limitations and safety conditions
- No model-based entailment or contradiction result has been verified on a real live API. Mock successes cannot establish factual accuracy.
- Source-domain scores are unvalidated heuristics, not external fact checking or proof of publisher reliability. Independent information validation and human editorial review remain necessary.
- The gate does not yet semantically verify every nonnumeric phrase in every section, hook or CTA against its citations. This is a blocker for autonomous public publishing.
- The contradiction model can still fail to recognize a real contradiction even when every pair is presented. Human review needed.
- Stronger URL content authenticity checks, scholarly citation quality, source independence, fact freshness and copyright licensing checks remain outside this module.
- The router's free-tier no-billing status and real GitHub deployment remain unverified; live tests disabled.
- Publishing must remain off. No automatic public publishing supported by this package.
