# Task 8 narration smoke: review and patch

This patch deliberately **reuses the corrected Task 8 `narration_pro/` implementation**, rather than the incomplete duplicate aligner and caption logic in the proposed workflow.

## What's changed

- A successful run ALWAYS invokes actual Piper neural synthesis, real WhisperX CTC word alignment, and FFmpeg. No `run_aligner=false` synthetic timestamps are possible.
- A full dependency installation resolves WhisperX's official dependency graph (instead of `--no-deps` plus a partial replacement list).
- CI uses `set -euo pipefail` so synthesis failures cannot be hidden by `tee`.
- `pip check` and `torch.version.cuda is None` require a self-consistent CPU-only installation.
- Piper models are downloaded using the documented `--data-dir` option, with `.onnx` and `.onnx.json` required.
- An independent gate rechecks complete ordered transcript coverage, word timestamps, ASS captions (max 2 lines / 32 characters), actual H.264/AAC Full HD streams, A/V duration and **measured** LUFS / true peak.
- Read-only GitHub `contents` permissions, manual trigger, short artifact retention, and no YouTube upload.

## Local tests completed

```
python -m compileall -q scripts tests narration_pro
python -m pytest -q tests/test_narration_smoke_guards.py tests/test_narration_pro.py
```

**Observed:** 20 passed. One of the 20 tests rendered a real 1920×1080 H.264/AAC test video with an FFmpeg sine tone. This **is not** a real Piper/WhisperX run.

## How to use

1. Merge this directory into the root of your **existing Task 8** repository; only the new smoke workflow, scripts, and tests are required if `narration_pro/` and the pinned requirements are already present.
2. Confirm your GitHub Actions allowance **before running**. Private-repository Actions minutes, storage, and caches can cost money beyond included limits. No free tier or zero-billing guarantee is implied.
3. On your own GitHub repo, use **Actions → Task 8 Narration Smoke → Run workflow**. Run only once while validating; download and listen to artifacts after execution.
4. Examine run logs. A passing run is evidence for that environment only. Human review of naturalness and caption alignment is still required.

We have **NOT** pushed to GitHub, installed Piper/WhisperX in the review environment, downloaded acoustic models, or obtained real neural narration. CI success is unknown.

## Primary documentation
- WhisperX deps: https://github.com/m-bain/whisperX/blob/main/pyproject.toml
- Piper downloader: https://github.com/OHF-Voice/piper1-gpl
- LibriTTS voice lineage: https://huggingface.co/rhasspy/piper-voices/blob/main/en/en_US/libritts/high/MODEL_CARD
- GitHub Actions billing: https://docs.github.com/en/billing/concepts/product-billing/github-actions

Note: the LibriTTS model card reports **dataset** CC BY 4.0. Commercial production still requires compliance with model, corpus, dependency and output-use terms; do not treat a dataset license as the entire legal review.
