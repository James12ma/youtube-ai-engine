# Task 8: Neural narration + real CTC word alignment

## Tested in this work session

- `python -m compileall -q narration_pro tests`: passes.
- `pytest -q`: **155 passed, 3 skipped**, with all 13 new Task 8 offline tests passing.
- A real FFmpeg loudness normalization test passed using generated sine audio.
- Piper is **NOT installed** and no voice model is present in this container.
- WhisperX is **NOT installed**, no CTC alignment model is present.
- Therefore no real neural voice, word alignment, or new voice sample MP4 was produced. Tests use mocked adapters for Piper and WhisperX. Previous Task 7 MP4 is NOT a Task 8 neural sample.

## Compatibility fix

The supplied pins were internally contradictory. `whisperx==3.8.6` declares:
- `torch~=2.8.0`, `torchaudio~=2.8.0`, `torchvision~=0.23.0`, `numpy>=2.1.0`.
- The originally supplied `torch==2.5.1`, `torchaudio==2.5.1`, and `numpy==1.26.4` cannot resolve with that release.
- See https://raw.githubusercontent.com/m-bain/whisperX/v3.8.6/pyproject.toml

We now give compatible **declared version constraints** in `requirements-narration.txt`; installation of that set was not tested. Use a separate virtual environment (`python3.12 -m venv .venv-narration`) and install platform-specific CPU PyTorch/torchaudio. WhisperX may transitively pull additional dependencies including Triton on Linux x86_64. Confirm the environment and access to models before claiming production readiness.

## Corrections compared with DeepSeek Task 8

1. Guard against missing `.onnx.json` and empty WAV.
2. Check actual CTC alignment covers the original transcript (LCS token coverage >=95%), reject missing words, invalid and out-of-order times. No estimated timing fallback.
3. Enforce caption line breaks (ASS `\\N`) of at most 32 characters and two lines; reject oversized words.
4. QA checks caption text identity as well as temporal coverage; do not penalize natural pauses in speech.
5. Use `target_offset` from FFmpeg's first loudnorm pass and verify final LUFS/true peak.
6. Add an optional real sample script that generates an actual WAV, timestamp JSON, ASS and MP4 *only when dependencies and voices are installed*.

## Commercial rights

The official `en_US-libritts-high` model card says the training dataset was LibriTTS `train-clean-360`, CC BY 4.0; the Piper voices repository as a whole shows MIT. This is not an unconditional legal guarantee about every redistributed model or output. Read the exact voice model card/license, retain attribution and review dependencies before monetized publication:
https://huggingface.co/rhasspy/piper-voices/blob/main/en/en_US/libritts/high/MODEL_CARD

The Piper 1.8 package is GPL-3.0-or-later. GPL obligations can arise if you distribute software; using a local tool to make a video is a different fact pattern. Review your actual use and distribution model. WhisperX 3.8.6 is BSD-2-Clause.

## Commands

```bash
# Run existing offline suite (no models, network, keys or fees):
python -m compileall -q narration_pro tests
pytest -q

# Separate environment, once adequate disk and network are available:
python3.12 -m venv .venv-narration
source .venv-narration/bin/activate
pip install -r requirements-narration.txt
python -m piper.download_voices en_US-libritts-high
# Locate the ONNX model AND its .onnx.json file; downloader location may vary.
# WhisperX alignment model downloads must also be available for its first run.
python run_task8_sample.py --model /ACTUAL/PATH/en_US-libritts-high.onnx \
    --output task8_real_output
```

This sample outputs a **clearly labeled original demonstration background**, not a third-party UI; it is to verify the neural narration and word alignment only. Visual polish requires a subsequent editing workflow and manual viewing/listening.
