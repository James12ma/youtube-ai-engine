# English Chatterbox for the 98-second LogicScript motion proof

Reuses `channel/voices.py` ChatterboxEngine and `scripts/voice_compare.py` loader.
This is not a new TTS provider or a paid API.

## Backend choice
- `chatterbox-en`: existing English-only Chatterbox model (`english_model=True`).
- `chatterbox-en-mtl`: existing multilingual model in `language='en'` mode.
- Both set `latam=False`: they never use/change Alan7's Spanish fine-tune.
- Neither clones a real person's voice (`reference_wav=None`).
- English model weights may need first-time free download and compute time.
- Missing dependencies/models fail closed; eSpeak is never substituted.

## Audition BEFORE the full 98s render
```bash
python -m tiktok_motion.reference15.chatterbox_voice \
  --sample-out outputs/career_english_sample.wav \
  --backend chatterbox-en --device cpu
```
Listen and get explicit owner approval. Only opening narration is generated.
If CPU is too slow, use an already available free GPU; no billable compute.

## Generate 98s video with English voice, without rerendering visuals
```bash
python -m tiktok_motion.reference15.chatterbox_voice \
  --input /path/to/LogicScript_5_Job_Interview_Formats_98s.mp4 \
  --output outputs/career_98s_chatterbox_en.mp4 \
  --backend chatterbox-en --device cpu
```
The original 98s MP4 must be supplied locally; the repo does not contain that video.
All seven narrations must fit their slots; words are never chopped or time-stretched.
The previous eSpeak audio is excluded; the original H.264 video is preserved.
No upload, publish, deploy, merge, or changes to core Alan7/LogicScript modules.

## Offline contract tests
```bash
python -m unittest -v tests.test_chatterbox_career_voice
```
These tests intentionally do not fetch/load Chatterbox weights.
A passing contract test is not evidence of natural voice quality;
only a listened-to sample and actual render can establish that.
