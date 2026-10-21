# Finance integration — isolated review only

Branch: `feature/finance-integration-reviewed`
Base: `e05cf3520e1093182ff7e2d262df6c40ed42a409`

## What changed

- `orchestrator/finance_planner.py`: Router-based structured visual scene planning, no independent video compositor.
- `orchestrator/finance_runtime.py`: integrates the existing Router and approved free-tier adapters.
- `scripts/premium_private_job.py`: after Telegram source-file retrieval and original-script SHA256 validation, optionally generates a finance scene plan. Blocks with private owner-review metadata if planning fails.
- `alan7_bot/src/index.js`: adds owner-only `/finance en <script>`; reuses premium_video job kind and original private Telegram document mechanism.
- `.github/workflows/alan7-premium-video.yml`: narrowly allows `mode=finance`, explicit `FINANCE_LLM_APPROVED` gate, and requires at least one free-provider key. All other modes are not granted Router access.
- `tests/test_finance_plan.py`: offline Pydantic and existing `premium_job.make_plan` contract tests.
- `tests/verify_style_distinctness.py`: dHash visual-difference *smoke* test. Not semantic or creative quality assessment.

## Safety

- Default finance LLM execution remains **disabled**. The owner must explicitly configure `FINANCE_LLM_APPROVED=1` on the repository AND an appropriate free-provider secret before a finance job can run.
- Do not enable any key tied to billable services. Actual account/provider free-tier eligibility must be verified independently.
- All other premium modes retain their existing behavior.
- No uploads or YouTube publication, merge or Cloudflare Worker deployment is performed in this branch.
- Original owner script must be preserved exactly after whitespace normalization, or the planner blocks.
- Numeric visuals are illustrative only, labeled **Illustrative** on screen. External claim verification is **not** implemented.
- Text excerpts are only accepted with an explicit "Illustrative example" label unless a future source-verification system is integrated.

## Known limitations / blockers

1. A financial test has NOT been rendered. There is no verified 58–62 second 1080p MP4 or reviewed frames.
2. A storyboard may have three different components; **four verified semantically meaningful styles is not enforced**. The conceptual map is rejected if not narratively relevant.
3. No B-roll, arbitrary 3D animation, true location maps, cross-video character identity or open-ended cinematic editing is added.
4. The finance planner works with an existing complete script, not a topic alone. It must not rewrite narration.
5. Passing chart numeric validators or labeling illustrative does not independently verify actual historical facts.
6. `StateStore` uses an isolated checkout state with `push_required=False` for review; confirm Git worktree behavior in an actual branch runner.
7. Current isolated branch has not been deployed to Cloudflare. The owner's live Alan7 Telegram bot cannot invoke this branch's new command until an explicitly approved deployment.
8. GitHub Actions and offline pytest have not been run by this review; no success claim is permitted without actual results.

## Verification commands for an approved $0 environment

```bash
python -m pytest tests/test_finance_plan.py -v
python -m compileall -q orchestrator/finance_planner.py orchestrator/finance_runtime.py scripts/premium_private_job.py
git diff --check e05cf3520e1093182ff7e2d262df6c40ed42a409...HEAD
```

A complete acceptance run also requires validating output streams and duration with ffprobe; extracting frames based on the *actual scene start/end timestamps*, not assumed [3,18,30,45]; reviewing them manually; and recording results in a report. A visually different dHash does not prove semantic quality.
