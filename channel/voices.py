"""Narration voices for Alan7 — free, local, commercial use allowed.

Engines (all run on our own runners, no paid service):
- piper      : current voice (Piper 1.8, es_MX-claude-high, MIT/GPL-free voice data per model card).
- kokoro     : Kokoro-82M (Apache-2.0), Spanish voices em_alex / em_santa / ef_dora.
- chatterbox : Resemble AI Chatterbox multilingual (MIT) with the Latin-American Spanish
               fine-tune (ResembleAI/Chatterbox-Multilingual-es-mx-latam, MIT). Expressive,
               "exaggeration" control; clones the timbre of a reference clip. We only use
               SYNTHETIC reference clips (no real person's voice). Output carries Resemble's
               inaudible Perth watermark.

Excluded on purpose: XTTS-v2 / F5-TTS / Fish-Speech / Spark-TTS (non-commercial licences),
Edge "read aloud" voices (not licensed for this use), ElevenLabs free tier (no commercial use).

Narration is synthesised sentence by sentence and assembled with pauses chosen from the
punctuation (story rhythm), instead of one flat block of text.
"""
from __future__ import annotations
import re
import wave
from dataclasses import dataclass
from pathlib import Path

import numpy as np

SR_OUT = 24000
PAUSES = {'…': 0.65, '.': 0.42, '?': 0.55, '!': 0.45, ':': 0.35, ';': 0.3}
PARAGRAPH_PAUSE = 0.9


@dataclass
class Sentence:
    text: str
    pause_after: float


def split_story(text: str) -> list[Sentence]:
    """Sentences with the pause that should follow each one ('\n\n' = paragraph break)."""
    out: list[Sentence] = []
    for para in [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]:
        parts = re.findall(r'[^.!?…:;]+(?:\.\.\.|[.!?…:;]+)?', ' '.join(para.split()))
        parts = [p.strip() for p in parts if p.strip()]
        # glue very short fragments (e.g. "y" after an ellipsis) to the next sentence
        merged: list[str] = []
        for p in parts:
            if merged and len(merged[-1].split()) < 2 and not merged[-1].endswith(('?', '!')):
                merged[-1] = merged[-1] + ' ' + p
            else:
                merged.append(p)
        for i, p in enumerate(merged):
            end = p.replace('...', '…')[-1]
            pause = PAUSES.get(end, 0.3)
            if i == len(merged) - 1:
                pause = max(pause, PARAGRAPH_PAUSE)
            out.append(Sentence(p, pause))
    if out:
        out[-1].pause_after = 0.0
    return out


def _resample(x: np.ndarray, sr: int, target: int = SR_OUT) -> np.ndarray:
    if sr == target:
        return x.astype(np.float32)
    import librosa
    return librosa.resample(x.astype(np.float32), orig_sr=sr, target_sr=target)


def _trim(x: np.ndarray, sr: int, db: float = 40) -> np.ndarray:
    import librosa
    y, _ = librosa.effects.trim(x, top_db=db)
    pad = int(0.03 * sr)
    return np.concatenate([np.zeros(pad, np.float32), y.astype(np.float32), np.zeros(pad, np.float32)])


class PiperEngine:
    name = 'piper'

    def __init__(self, model: Path, length_scale: float = 1.0, noise_scale: float = 0.667, noise_w: float = 0.8):
        from piper import PiperVoice, SynthesisConfig
        self.voice = PiperVoice.load(str(model), config_path=str(model) + '.json', use_cuda=False)
        self.cfg = SynthesisConfig(length_scale=length_scale, noise_scale=noise_scale, noise_w_scale=noise_w)
        self.sr = self.voice.config.sample_rate

    def say(self, text: str) -> np.ndarray:
        chunks = [c.audio_float_array for c in self.voice.synthesize(text, syn_config=self.cfg)]
        return np.concatenate(chunks) if chunks else np.zeros(1, np.float32)


class KokoroEngine:
    name = 'kokoro'

    def __init__(self, voice: str = 'em_alex', speed: float = 1.0):
        from kokoro import KPipeline
        self.pipe = KPipeline(lang_code='e', repo_id='hexgrad/Kokoro-82M')
        self.voice, self.speed, self.sr = voice, speed, 24000

    def say(self, text: str) -> np.ndarray:
        parts = [np.asarray(a, dtype=np.float32) for _, _, a in self.pipe(text, voice=self.voice, speed=self.speed)]
        return np.concatenate(parts) if parts else np.zeros(1, np.float32)


class ChatterboxEngine:
    name = 'chatterbox'

    def __init__(self, reference_wav: Path | None, *, latam: bool = True, exaggeration: float = 0.6,
                 cfg_weight: float = 0.4, temperature: float = 0.8, device: str = 'cpu', seed: int = 7,
                 language: str = 'es', english_model: bool = False, use_v3_decoder: bool = False):
        import shutil
        import torch
        from huggingface_hub import hf_hub_download, snapshot_download
        from chatterbox.mtl_tts import ChatterboxMultilingualTTS
        torch.manual_seed(seed)
        self.loaded = 'multilingual-v3'
        self.language = language
        self.english = None
        if english_model:   # Resemble's English-only model (MIT); same reference clip -> same timbre
            from chatterbox.tts import ChatterboxTTS
            self.english = ChatterboxTTS.from_pretrained(device=device)
            self.model, self.loaded = self.english, 'english'
        elif latam:
            base = Path(snapshot_download('ResembleAI/chatterbox', allow_patterns=[
                've.pt', 's3gen.pt', 'grapheme_mtl_merged_expanded_v1.json', 'conds.pt', 'Cangjie5_TC.json']))
            work = Path('/tmp/chatterbox_latam')
            work.mkdir(exist_ok=True)
            for f in base.iterdir():
                if not (work / f.name).exists():
                    shutil.copyfile(f, work / f.name)
            t3 = hf_hub_download('ResembleAI/Chatterbox-Multilingual-es-mx-latam', 't3_es_mx_latam.safetensors')
            shutil.copyfile(t3, work / 't3_es_mx_latam.safetensors')
            # The owner approved the voice made with the BASE decoder (Oct 2026). The fine-tune's own V3 decoder
            # is only tried when asked (it changes the sound; needs a new listening test before it is used).
            try:
                if not use_v3_decoder:
                    raise RuntimeError('base decoder kept (approved voice)')
                s3 = hf_hub_download('ResembleAI/Chatterbox-Multilingual-es-mx-latam', 's3gen_v3.pt')
                (work / 's3gen.pt').unlink(missing_ok=True)   # cache copies are read-only
                shutil.copyfile(s3, work / 's3gen.pt')
                self.loaded = 'es-mx-latam (t3 + s3gen_v3)'
            except Exception as exc:   # keep the reason: it may affect pronunciation quality
                self.loaded = f'es-mx-latam (t3) + base s3gen [s3gen_v3 unavailable: {type(exc).__name__}: {str(exc)[:120]}]'
            self.model = ChatterboxMultilingualTTS.from_local(work, device, t3_model='t3_es_mx_latam.safetensors')
        else:
            self.model = ChatterboxMultilingualTTS.from_pretrained(device=device, t3_model='v3')
        self.ref = str(reference_wav) if reference_wav else None
        self.kw = dict(exaggeration=exaggeration, cfg_weight=cfg_weight, temperature=temperature)
        self.sr = self.model.sr

    def say(self, text: str) -> np.ndarray:
        if self.english is not None:
            wav = self.model.generate(text, audio_prompt_path=self.ref, **self.kw)
        else:
            wav = self.model.generate(text, language_id=self.language, audio_prompt_path=self.ref, **self.kw)
        return wav.squeeze().cpu().numpy().astype(np.float32)


def narrate(engine, text: str, out: Path, *, sentence_level: bool = True) -> dict:
    """Synthesise ``text`` and write a 24 kHz mono WAV. Returns timing info."""
    pieces, timeline = [], []
    t = 0.0
    sents = split_story(text) if sentence_level else [Sentence(' '.join(text.split()), 0.0)]
    for s in sents:
        x = _trim(_resample(engine.say(s.text), engine.sr), SR_OUT)
        pieces += [x, np.zeros(int(s.pause_after * SR_OUT), np.float32)]
        timeline.append({'text': s.text, 'start_s': round(t, 2), 'seconds': round(len(x) / SR_OUT, 2),
                         'pause_after': s.pause_after})
        t += len(x) / SR_OUT + s.pause_after
    audio = np.concatenate(pieces) if pieces else np.zeros(1, np.float32)
    peak = float(np.max(np.abs(audio)) or 1.0)
    audio = (audio / peak * 0.89 * 32767).astype(np.int16)
    out.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out), 'wb') as fh:
        fh.setnchannels(1); fh.setsampwidth(2); fh.setframerate(SR_OUT); fh.writeframes(audio.tobytes())
    return {'engine': engine.name, 'seconds': round(len(audio) / SR_OUT, 2), 'sentences': timeline}


def prosody(path: Path) -> dict:
    """Simple, explainable expressiveness numbers: pitch range/variation, pauses, speaking rate."""
    import librosa
    y, sr = librosa.load(str(path), sr=16000)
    f0, voiced, _ = librosa.pyin(y, fmin=60, fmax=400, sr=sr, frame_length=1024)
    f0 = f0[voiced & ~np.isnan(f0)]
    if len(f0) < 10:
        return {'error': 'no voiced frames'}
    st = 12 * np.log2(f0 / np.median(f0))
    intervals = librosa.effects.split(y, top_db=35)
    gaps = [(b0 - a1) / sr for (_, a1), (b0, _) in zip(intervals[:-1], intervals[1:])]
    return {'pitch_median_hz': round(float(np.median(f0)), 1),
            'pitch_std_semitones': round(float(np.std(st)), 2),               # flat robotic voices: low
            'pitch_range_semitones': round(float(np.percentile(st, 95) - np.percentile(st, 5)), 2),
            'pauses_over_0_25s': int(sum(1 for g in gaps if g > 0.25)),
            'duration_s': round(len(y) / sr, 2)}
