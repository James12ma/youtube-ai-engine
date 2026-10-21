"""Narration, sound effects and music for the Studio.

Narration backends
  kokoro    natural neural voice (Apache-2.0, CPU), native per-token timings. Used for real renders.
  estimate  no audio; word timings estimated from text. Only for offline drafts (never publishable).
Sound effects and music are synthesised here with numpy (no samples, no licence questions).
"""
from __future__ import annotations

import math
import re
import subprocess
import wave
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

SR = 48000
KOKORO_LANG = {'en': 'a', 'en-gb': 'b', 'es': 'e', 'fr': 'f', 'hi': 'h', 'it': 'i', 'ja': 'j', 'pt': 'p', 'zh': 'z'}
KOKORO_DEFAULT_VOICE = {'a': 'af_heart', 'b': 'bf_emma', 'e': 'ef_dora', 'f': 'ff_siwis', 'h': 'hf_alpha',
                        'i': 'if_sara', 'j': 'jf_alpha', 'p': 'pf_dora', 'z': 'zf_xiaobei'}
TOKEN_RE = re.compile(r"[a-z0-9]+(?:'[a-z0-9]+)?")


def tokens(text: str) -> list[str]:
    return TOKEN_RE.findall(text.casefold().replace('’', "'"))


@dataclass
class BeatAudio:
    text: str
    words: list[dict]                 # [{'text','start','end'}] seconds, relative to this beat
    duration: float
    wav: Path | None = None


@dataclass
class Narration:
    backend: str
    beats: list[BeatAudio] = field(default_factory=list)

    @property
    def is_draft(self) -> bool:
        return self.backend == 'estimate'


# ---------------------------------------------------------------- narration backends
def estimate(texts: list[str], wps: float = 2.6) -> Narration:
    out = Narration('estimate')
    for text in texts:
        t, words = 0.0, []
        for raw in text.split():
            d = (1.0 / wps) * (1 + 0.045 * max(0, len(raw) - 6))
            words.append({'text': raw, 'start': round(t, 3), 'end': round(t + d * .9, 3)})
            t += d + (0.28 if re.search(r'[.!?]$', raw) else 0.12 if re.search(r'[,;:]$', raw) else 0)
        out.beats.append(BeatAudio(text, words, round(t + .1, 3)))
    return out


def kokoro(texts: list[str], out_dir: Path, *, language: str = 'en', voice: str = '', pipeline=None) -> Narration:
    lang = KOKORO_LANG.get(language.lower(), 'a')
    voice = voice or KOKORO_DEFAULT_VOICE[lang]
    if pipeline is None:
        from kokoro import KPipeline
        pipeline = KPipeline(lang_code=lang, repo_id='hexgrad/Kokoro-82M')
    out = Narration('kokoro:' + voice)
    out_dir.mkdir(parents=True, exist_ok=True)
    for i, text in enumerate(texts):
        chunks, words, offset = [], [], 0.0
        for result in pipeline(text, voice=voice, speed=1.0):
            audio = np.asarray(result.audio, dtype=np.float32)
            if not len(audio) or not np.isfinite(audio).all():
                raise ValueError('invalid generated speech')
            for tok in result.tokens or []:
                a, b, w = getattr(tok, 'start_ts', None), getattr(tok, 'end_ts', None), getattr(tok, 'text', '')
                if a is None or b is None or not str(w).strip() or b <= a:
                    continue
                words.append({'text': str(w), 'start': round(float(a) + offset, 3), 'end': round(float(b) + offset, 3)})
            chunks.append(audio); offset += len(audio) / 24000
        if not chunks or not words:
            raise ValueError(f'beat {i}: speech or token timing missing')
        wav = out_dir / f'beat_{i:02d}.wav'
        write_wav(wav, np.concatenate(chunks), 24000)
        out.beats.append(BeatAudio(text, _merge_punct(words), round(offset, 3), wav))
    return out


def _merge_punct(words: list[dict]) -> list[dict]:
    """Kokoro emits punctuation as separate tokens; attach them to the previous word."""
    out = []
    for w in words:
        if out and re.fullmatch(r"[^\w$€£%]+", w['text']):
            out[-1]['text'] += w['text']; out[-1]['end'] = max(out[-1]['end'], w['end'])
        else:
            out.append(dict(w))
    return out


# ---------------------------------------------------------------- wav helpers
def write_wav(path: Path, data: np.ndarray, sr: int = SR) -> Path:
    data = np.clip(np.asarray(data, dtype=np.float32), -1, 1)
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((data * 32767).astype('<i2').tobytes())
    return Path(path)


def read_wav(path: Path) -> tuple[np.ndarray, int]:
    with wave.open(str(path)) as w:
        sr, n, ch = w.getframerate(), w.getnframes(), w.getnchannels()
        data = np.frombuffer(w.readframes(n), dtype='<i2').astype(np.float32) / 32767
    return (data.reshape(-1, ch).mean(axis=1) if ch > 1 else data), sr


def resample(x: np.ndarray, sr: int, to: int = SR) -> np.ndarray:
    if sr == to:
        return x
    idx = np.arange(0, len(x) * to / sr) * sr / to
    return np.interp(idx, np.arange(len(x)), x).astype(np.float32)


# ---------------------------------------------------------------- sound design (synthesised)
def _env(n, a=0.005, r=0.08):
    t = np.arange(n) / SR
    return np.minimum(1, t / max(a, 1e-4)) * np.exp(-t / max(r, 1e-4))


def sfx(kind: str, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    if kind == 'click':
        n = int(.06 * SR); t = np.arange(n) / SR
        return (np.sin(2 * np.pi * 2400 * t) * .5 + rng.normal(0, .3, n)) * _env(n, .001, .012) * .5
    if kind == 'pop':
        n = int(.14 * SR); t = np.arange(n) / SR
        f = 520 + 380 * np.exp(-t * 30)
        return np.sin(2 * np.pi * np.cumsum(f) / SR) * _env(n, .002, .05) * .45
    if kind == 'whoosh':
        n = int(.45 * SR); noise = rng.normal(0, 1, n)
        k = np.hanning(n); out = np.convolve(noise, np.ones(40) / 40, mode='same') * k
        return out / (np.abs(out).max() + 1e-9) * .32
    if kind == 'chime':
        n = int(.9 * SR); t = np.arange(n) / SR
        tone = sum(np.sin(2 * np.pi * f * t) * a for f, a in ((880, .5), (1320, .3), (1760, .15)))
        return tone * _env(n, .003, .35) * .35
    if kind == 'tick':
        n = int(.025 * SR)
        return rng.normal(0, 1, n) * _env(n, .0005, .006) * .18
    if kind == 'thud':
        n = int(.3 * SR); t = np.arange(n) / SR
        return np.sin(2 * np.pi * (90 + 60 * np.exp(-t * 25)) * t) * _env(n, .002, .12) * .6
    return np.zeros(1, dtype=np.float32)


SFX_FOR_CUE = [  # (cue name prefix, effect)
    ('tap', 'click'), ('click', 'click'), ('toggle', 'click'), ('open', 'click'),
    ('send', 'whoosh'), ('walk', 'whoosh'),
    ('arrive', 'chime'), ('success', 'chime'), ('done', 'chime'), ('notify', 'chime'), ('stamp', 'thud'), ('verdict', 'thud'),
    ('pop', 'pop'), ('row', 'pop'), ('step', 'pop'), ('incoming', 'pop'), ('status', 'pop'), ('callout', 'pop'),
    ('say', 'pop'), ('prop', 'pop'), ('options', 'pop'), ('light', 'pop'),
]


def effects_for(cues: list[dict], shot_starts: list[float]) -> list[tuple[float, str]]:
    out = []
    for c in cues:
        for prefix, kind in SFX_FOR_CUE:
            if c['name'] == prefix or c['name'].startswith(prefix + ':') or c['name'].startswith(prefix + '-'):
                out.append((c['at'], kind)); break
        if c['name'].startswith('type'):
            dur = float((c.get('args') or {}).get('dur', 1.0))
            out += [(c['at'] + k * .085, 'tick') for k in range(int(dur / .085))]
    out += [(max(0.0, s - .12), 'whoosh') for s in shot_starts[1:]]
    return sorted(out)


def music(mood: str, seconds: float, seed: int = 3) -> np.ndarray:
    """A quiet, original bed: soft chords (soft), muted pulse (pulse) or bright plucks (playful)."""
    n = int(seconds * SR); t = np.arange(n) / SR; out = np.zeros(n, dtype=np.float32)
    if mood == 'none':
        return out
    chords = [(220.0, 277.18, 329.63), (196.0, 246.94, 293.66), (174.61, 220.0, 261.63), (196.0, 246.94, 329.63)]
    bar = 2.4 if mood != 'playful' else 1.6
    for k in range(int(seconds / bar) + 1):
        a, b = int(k * bar * SR), min(n, int((k + 1) * bar * SR))
        if a >= n:
            break
        seg = t[a:b] - k * bar; ch = chords[k % len(chords)]
        if mood == 'pulse':
            env = np.exp(-((seg * 4) % 1) * 5) * .6 + .1
            out[a:b] += sum(np.sin(2 * np.pi * f / 2 * seg) for f in ch) * env * .05
        elif mood == 'playful':
            for j, f in enumerate(ch):
                st = j * bar / 3; m = seg >= st
                out[a:b] += np.where(m, np.sin(2 * np.pi * f * 2 * (seg - st)) * np.exp(-(seg - st) * 6), 0) * .06
        else:
            env = np.minimum(1, seg / .6) * np.minimum(1, (bar - seg) / .6)
            out[a:b] += sum(np.sin(2 * np.pi * f * seg) + .3 * np.sin(2 * np.pi * f * 2 * seg) for f in ch) * env * .035
    fade = np.minimum(1, np.minimum(t / 1.5, (seconds - t) / 2.0))
    return (out * np.clip(fade, 0, 1)).astype(np.float32)


def mix(out: Path, duration: float, narration: Narration, beat_starts: list[float],
        effects: list[tuple[float, str]], mood: str) -> Path:
    n = int(math.ceil(duration * SR)); bus = np.zeros(n, dtype=np.float32)
    voice = np.zeros(n, dtype=np.float32)
    for beat, start in zip(narration.beats, beat_starts):
        if beat.wav is None:
            continue
        x, sr = read_wav(beat.wav); x = resample(x, sr)
        a = int(start * SR); b = min(n, a + len(x)); voice[a:b] += x[:b - a]
    peak = np.abs(voice).max()
    if peak > 0:
        voice *= .89 / peak
    fx = np.zeros(n, dtype=np.float32)
    for i, (at, kind) in enumerate(effects):
        s = sfx(kind, i); a = int(at * SR); b = min(n, a + len(s))
        if 0 <= a < n:
            fx[a:b] += s[:b - a]
    bed = np.zeros(n, dtype=np.float32); m = music(mood, duration)[:n]; bed[:len(m)] = m
    # duck the music under speech
    if peak > 0:
        env = np.convolve(np.abs(voice), np.ones(SR // 10) / (SR // 10), mode='same')
        bed *= np.clip(1 - env * 4, .35, 1)
    bus = voice + fx * .7 + bed
    bus /= max(1.0, np.abs(bus).max() / .97)
    raw = out.with_suffix('.raw.wav'); write_wav(raw, bus)
    if peak > 0:
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', str(raw), '-af', 'loudnorm=I=-16:TP=-1.5:LRA=11',
                        '-ar', str(SR), '-ac', '1', str(out)], check=True)
        raw.unlink()
    else:
        raw.replace(out)
    return out
