"""Voice Director: narration -> voice.wav + per-word times aligned to the spec's word indices.

Kokoro-82M (Apache-2.0) gives native word timestamps. Languages: en, es, fr, pt (Kokoro). Haitian
Creole has no good free voice yet: it is reported as a capability gap rather than read with a wrong
accent.

    python -m studio.voice studio/films/gate_a [--voice af_heart] [--speed 1.0]
"""
from __future__ import annotations

import json
import re
import wave
from pathlib import Path

import numpy as np

from .spec import FilmSpec, tokenize

SR = 24000
LANG = {"en": ("a", "af_heart"), "es": ("e", "ef_dora"), "fr": ("f", "ff_siwis"), "pt": ("p", "pf_dora")}


def _norm(s: str) -> str:
    return re.sub(r"[^\w]", "", s.lower().replace("’", "'"))


def align(words: list[str], tokens: list[tuple[str, float | None, float | None]]) -> list[tuple[float, float]]:
    """Map our words onto engine tokens in order; tokens may merge or split words and include punctuation."""
    toks = [(_norm(t), a, b) for t, a, b in tokens if _norm(t)]
    out: list[tuple[float | None, float | None]] = []
    j = 0
    for w in words:
        target = _norm(w)
        hit = None
        acc, start = "", None
        for k in range(j, min(j + 6, len(toks))):
            if start is None:
                acc, start = "", k
            acc += toks[k][0]
            if acc == target or toks[k][0] == target:
                hit = (start if acc == target else k, k)
                break
            if not target.startswith(acc):
                acc, start = "", None
        if hit:
            a, b = toks[hit[0]][1], toks[hit[1]][2]
            out.append((a, b))
            j = hit[1] + 1
        else:
            out.append((None, None))
    # Fill gaps (unmatched words or missing timestamps) by interpolation between known neighbours.
    times = [list(x) for x in out]
    for i, (a, b) in enumerate(times):
        if a is None or b is None:
            prev = next((times[k][1] for k in range(i - 1, -1, -1) if times[k][1] is not None), 0.0)
            nxt = next((times[k][0] for k in range(i + 1, len(times)) if times[k][0] is not None), prev + 0.4)
            times[i] = [prev + 0.02, max(prev + 0.1, nxt - 0.02)]
    return [(round(a, 3), round(b, 3)) for a, b in times]


def synthesize(text: str, language: str, voice: str | None = None, speed: float = 1.0):
    if language not in LANG:
        raise SystemExit(f"capability gap: no free natural voice for language '{language}'")
    from kokoro import KPipeline  # noqa: PLC0415 - heavy, runner only

    code, default = LANG[language]
    pipe = KPipeline(lang_code=code, repo_id="hexgrad/Kokoro-82M")
    audio, tokens, offset = [], [], 0.0
    for result in pipe(text, voice=voice or default, speed=speed, split_pattern=r"(?<=[.!?])\s+"):
        chunk = result.audio.numpy() if hasattr(result.audio, "numpy") else np.asarray(result.audio)
        for t in result.tokens or []:
            a = None if t.start_ts is None else offset + t.start_ts
            b = None if t.end_ts is None else offset + t.end_ts
            tokens.append((t.text, a, b))
        pause = np.zeros(int(0.12 * SR), dtype=np.float32)  # breath between sentences
        audio += [chunk.astype(np.float32), pause]
        offset += len(chunk) / SR + len(pause) / SR
    return np.concatenate(audio), tokens


def write_wav(path: Path, x: np.ndarray) -> None:
    x = x / max(1e-9, float(np.max(np.abs(x)))) * 0.89  # ~ -1 dBFS peak
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((x * 32767).astype("<i2").tobytes())


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("film", type=Path)
    ap.add_argument("--voice")
    ap.add_argument("--speed", type=float, default=1.0)
    ap.add_argument("--out", type=Path, help="output folder (default: the film folder)")
    a = ap.parse_args()
    spec = FilmSpec(**json.loads((a.film / "spec.json").read_text()))
    words = tokenize(spec.narration.text)
    audio, tokens = synthesize(spec.narration.text, spec.narration.language, a.voice, a.speed)
    out = a.out or a.film
    out.mkdir(parents=True, exist_ok=True)
    write_wav(out / "voice.wav", audio)
    times = align(words, tokens)
    matched = sum(1 for t in tokens if t[1] is not None)
    (out / "voice.json").write_text(json.dumps({
        "audio": "voice.wav", "engine": "kokoro-82m", "voice": a.voice or LANG[spec.narration.language][1],
        "duration_s": round(len(audio) / SR, 3), "word_times": times,
        "engine_tokens_with_time": matched, "words": len(words)}, indent=1))
    print(out / "voice.json", len(words), "words", round(len(audio) / SR, 2), "s")


if __name__ == "__main__":
    main()
