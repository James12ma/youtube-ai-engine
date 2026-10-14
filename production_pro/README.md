# Task 7 — genuine local software workflow (offline demo)

* Run: `python run_task7_demo.py --engineering-voice --size 1280x720` after installing `playwright` and `chromium`, FFmpeg, Pillow, and matplotlib.
* For real neural speech: `python run_task7_demo.py --piper-model /path/to/en_US-lessac-medium.onnx` after installing piper-tts and the corresponding ONNX and JSON files. Check model license separately. Audio word timings **are not claimed to be forced-aligned**.
* All demo numbers ($120 travel, $100 threshold) come from implemented sample decision rules, **not research claims**.
* Charts fail closed unless values can be reconciled with a source snippet, a Task 5 accepted claim and an actual cached source text. This is necessary but not sufficient for editorial fact-checking.
* No external site or SaaS, no publishing, no upload, no cloud API. A visual editor must still review narration and overall quality.
* VMAF/SSIM intentionally not displayed without valid reference. The QC checks actual codecs, loudness, black frames, silence, caption interval coverage, but cannot establish semantic quality.
