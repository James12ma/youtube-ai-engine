# YouTube AI Engine — Task 7 corrected local prototype

This archive preserves the local Tasks 1–6 modules and includes the corrected Task 7 `production_pro/` package and tests.

## Verify

```bash
python -m pip install -r requirements.txt -r requirements-dev.txt -r requirements-production.txt -r requirements-production-pro.txt
python -m playwright install chromium ffmpeg  # not needed if system Chromium + FFmpeg can be used
python -m compileall -q production_pro
pytest -q
```

## Demo with known robotic engineering voice (offline)

```bash
python run_task7_demo.py --engineering-voice --size 1920x1080 --output task7.mp4
```

This demo **requires** Playwright (Chromium), FFmpeg, espeak. It explicitly does not validate natural narrator quality.

## Demo with local Piper voice (must acquire voice first)

```bash
python -m pip install piper-tts
python -m piper.download_voices en_US-lessac-medium
python run_task7_demo.py --piper-model /ABSOLUTE/PATH/en_US-lessac-medium.onnx --output task7_piper.mp4
```

The `.onnx.json` file must be in the same directory. Verify the voice model's own commercial terms before using it in commercial videos. Timings will remain approximate until a forced aligner is added.

This is an **original functioning local demo**, not a real third-party SaaS product. It is not ready to publish.

See `TASK7_AUDIT.md` for all known limits and tests.
