"""Original synthesized UI/transition sound effects (no samples, no licences). 48 kHz mono WAV.

    python -m studio.audio.sfx studio/editor/public/sfx
"""
from __future__ import annotations

import sys
import wave
from pathlib import Path

import numpy as np

SR = 48000


def _env(n, attack, decay):
    t = np.arange(n) / SR
    return np.minimum(t / max(attack, 1e-4), 1.0) * np.exp(-t / decay)


def _sweep(n, f0, f1):
    f = np.linspace(f0, f1, n)
    return np.sin(2 * np.pi * np.cumsum(f) / SR)


def _noise(n, seed):
    return np.random.default_rng(seed).normal(0, 1, n)


def _lp(x, cutoff):
    a = np.exp(-2 * np.pi * cutoff / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc = (1 - a) * v + a * acc
        y[i] = acc
    return y


def tap():
    n = int(0.08 * SR)
    return _sweep(n, 1900, 900) * _env(n, 0.0005, 0.012) * 0.8 + _noise(n, 1) * _env(n, 0.0002, 0.003) * 0.25


def click():
    n = int(0.05 * SR)
    return _noise(n, 2) * _env(n, 0.0002, 0.004) * 0.6 + _sweep(n, 3200, 2600) * _env(n, 0.0004, 0.006) * 0.4


def type_():
    parts = []
    rng = np.random.default_rng(3)
    for _ in range(7):
        n = int(rng.uniform(0.06, 0.11) * SR)
        k = _noise(n, int(rng.integers(1e6))) * _env(n, 0.0003, 0.006) * rng.uniform(0.25, 0.45)
        parts.append(k)
    return np.concatenate(parts)


def pop():
    n = int(0.16 * SR)
    return _sweep(n, 380, 900) * _env(n, 0.002, 0.045)


def ding():
    n = int(1.2 * SR)
    t = np.arange(n) / SR
    tone = sum(np.sin(2 * np.pi * f * t) * a for f, a in [(1318.5, 0.6), (1975.5, 0.3), (2637, 0.12)])
    tone2 = sum(np.sin(2 * np.pi * f * t) * a for f, a in [(1760, 0.5), (2637, 0.2)])
    d = int(0.09 * SR)
    out = tone * _env(n, 0.002, 0.35)
    out[d:] += (tone2 * _env(n, 0.002, 0.4))[: n - d]
    return out * 0.5


def whoosh():
    n = int(0.65 * SR)
    shape = np.sin(np.pi * np.linspace(0, 1, n)) ** 2
    return _lp(_noise(n, 4), 1800) * shape * 2.2


def swoosh_up():
    n = int(0.5 * SR)
    shape = np.linspace(0, 1, n) ** 2 * np.exp(-np.linspace(0, 3, n))
    return _lp(_noise(n, 5), 2600) * shape * 3 + _sweep(n, 300, 1400) * shape * 0.15


def thud():
    n = int(0.5 * SR)
    t = np.arange(n) / SR
    f = 45 + 60 * np.exp(-t / 0.04)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * _env(n, 0.002, 0.15)


def ring():
    n = int(1.6 * SR)
    t = np.arange(n) / SR
    burst = (np.sin(2 * np.pi * 880 * t) + np.sin(2 * np.pi * 1108.7 * t)) * (np.sin(2 * np.pi * 18 * t) > 0)
    gate = ((t % 0.8) < 0.45).astype(float)
    return burst * gate * np.exp(-t / 1.5) * 0.35


SOUNDS = {"tap": tap, "click": click, "type": type_, "pop": pop, "ding": ding, "whoosh": whoosh,
          "swoosh_up": swoosh_up, "thud": thud, "ring": ring}


def write_all(out: Path) -> list[Path]:
    out.mkdir(parents=True, exist_ok=True)
    paths = []
    for name, fn in SOUNDS.items():
        x = fn()
        x = x / max(1e-9, np.max(np.abs(x))) * 0.7
        p = out / f"{name}.wav"
        with wave.open(str(p), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes((x * 32767).astype("<i2").tobytes())
        paths.append(p)
    return paths


if __name__ == "__main__":
    for p in write_all(Path(sys.argv[1] if len(sys.argv) > 1 else "studio/editor/public/sfx")):
        print(p)
