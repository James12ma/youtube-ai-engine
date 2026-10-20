"""Synthesised sound design for the Focus prototype (no samples, no licences needed).

Cues are derived from ../timeline.json so audio stays locked to picture:
ambient pad, hero landing thud, dot pops, headline whooshes, UI click, ring chime.

    python make_score.py --out ../remotion/public/audio/score.wav
"""
from __future__ import annotations

import argparse
import json
import random
import wave
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
TL = json.loads((HERE.parent / "timeline.json").read_text())
B, FPS = TL["beats"], TL["fps"]
SR = 48000
DUR = TL["frames"] / FPS
N = int(SR * DUR)
t_all = np.arange(N) / SR


def sec(frame: float) -> float:
    return frame / FPS


def env(n, attack, decay):
    t = np.arange(n) / SR
    return np.minimum(t / max(attack, 1e-4), 1.0) * np.exp(-t / decay)


def place(buf, start_s, sig, pan=0.0, gain=1.0):
    i = int(start_s * SR)
    if i >= N:
        return
    sig = sig[: N - i] * gain
    left, right = np.sqrt(0.5 * (1 - pan)), np.sqrt(0.5 * (1 + pan))
    buf[i:i + len(sig), 0] += sig * left
    buf[i:i + len(sig), 1] += sig * right


def lowpass(x, cutoff):
    a = np.exp(-2 * np.pi * cutoff / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc = (1 - a) * v + a * acc
        y[i] = acc
    return y


def pad():
    # Soft A-minor-add9 bed with slow swell into act 3.
    freqs = [110.0, 164.81, 220.0, 246.94, 329.63]
    sig = sum(np.sin(2 * np.pi * f * t_all + i) * (0.5 / (i + 1)) for i, f in enumerate(freqs))
    sig += 0.15 * np.sin(2 * np.pi * 440.0 * t_all) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.25 * t_all))
    swell = np.interp(t_all, [0, 1.2, sec(B["line3"][0]) - 0.5, sec(B["line3"][0]) + 1.2, DUR - 0.8, DUR],
                      [0, 0.35, 0.38, 0.75, 0.7, 0])
    return sig * swell * 0.12


def thud():
    n = int(0.6 * SR)
    t = np.arange(n) / SR
    f = 42 + 50 * np.exp(-t / 0.05)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.002, 0.18)
    click = np.random.default_rng(1).normal(0, 1, n) * env(n, 0.0005, 0.006) * 0.3
    return s + click


def pop(freq):
    n = int(0.09 * SR)
    t = np.arange(n) / SR
    f = freq * (1 + 0.6 * np.exp(-t / 0.01))
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.001, 0.025)


def whoosh(length=0.55):
    n = int(length * SR)
    noise = np.random.default_rng(2).normal(0, 1, n)
    shape = np.sin(np.pi * np.linspace(0, 1, n)) ** 2
    return lowpass(noise, 2200) * shape * 0.9


def tick():
    n = int(0.05 * SR)
    noise = np.random.default_rng(3).normal(0, 1, n)
    return (noise * env(n, 0.0003, 0.004) + np.sin(2 * np.pi * 2400 * np.arange(n) / SR) * env(n, 0.0005, 0.01)) * 0.8


def chime():
    n = int(2.2 * SR)
    t = np.arange(n) / SR
    return sum(np.sin(2 * np.pi * f * t) * a for f, a in [(880, 0.5), (1318.5, 0.35), (1760, 0.2), (2637, 0.08)]) * env(n, 0.004, 0.6)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=HERE.parent / "remotion/public/audio/score.wav")
    a = ap.parse_args()
    rnd = random.Random(7)
    buf = np.zeros((N, 2))
    p = pad()
    buf[:, 0] += p
    buf[:, 1] += p

    land = B["hero_drop"][0] + (B["hero_drop"][1] - B["hero_drop"][0]) * 0.62
    place(buf, sec(land), thud(), gain=0.9)
    for k in range(24):  # dots pop in centre-out (matches focus_scene.dot_scale timing)
        place(buf, sec(B["dots_in"][0] + k * 1.7 + 4), pop(rnd.uniform(900, 1500)), pan=rnd.uniform(-0.6, 0.6), gain=0.16)
    for k in range(24):  # ...and get swept away after the click, descending in pitch
        place(buf, sec(B["dots_out"][0] + k * 1.6 + 6), pop(1300 - k * 25), pan=rnd.uniform(-0.6, 0.6), gain=0.12)
    for f in (B["line1_big"][0], B["line2"][0] + 12, B["line3"][0] + 12):
        place(buf, sec(f) - 0.3, whoosh(), gain=0.22)
    place(buf, sec(B["dialog_in"][0]), pop(620), gain=0.3)
    place(buf, sec(B["cursor_click"]), tick(), gain=0.5)
    place(buf, sec(B["dialog_out"][0]) - 0.1, whoosh(0.4), gain=0.15)
    place(buf, sec(B["ring_in"][0]), chime(), gain=0.22)
    place(buf, sec(B["line3"][0] + 12), thud(), gain=0.45)

    buf /= np.max(np.abs(buf)) / 0.7  # peak ≈ -3 dBFS
    a.out.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(a.out), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((buf * 32767).astype("<i2").tobytes())
    print("wrote", a.out, f"{DUR:.2f}s")


if __name__ == "__main__":
    main()
