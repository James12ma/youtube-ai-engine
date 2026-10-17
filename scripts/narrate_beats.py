"""Narrate every beat of a documentary plan with the approved Alan7 voice (Chatterbox, Latin-American Spanish).

Runs in the Chatterbox virtualenv (its own torch/transformers pins), so it reads the plan as plain JSON.
Writes beat_<i>.wav (24 kHz mono) + manifest.json (text hash per beat, so the renderer can refuse
audio that does not match the plan). The timbre comes from a SYNTHETIC reference clip (Kokoro), never
from a real person's voice.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import time
from pathlib import Path

from scripts.voice_compare import _voices


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--plan', type=Path, required=True)
    ap.add_argument('--ref', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--seed', type=int, default=7)
    a = ap.parse_args()
    plan = json.loads(a.plan.read_text(encoding='utf-8'))
    v = _voices()
    eng = v.ChatterboxEngine(a.ref, latam=True, exaggeration=float(plan.get('voice_exaggeration', 0.6)),
                             cfg_weight=float(plan.get('voice_cfg', 0.4)), seed=a.seed)
    a.out.mkdir(parents=True, exist_ok=True)
    beats, t0 = [], time.time()
    for i, b in enumerate(plan['beats']):
        text = ' '.join(b['narration'].split())
        r = v.narrate(eng, text, a.out / f'beat_{i}.wav')
        beats.append({'index': i, 'sha1': hashlib.sha1(text.encode()).hexdigest(), 'seconds': r['seconds']})
        print(json.dumps({'beat': i, 'seconds': r['seconds'], 'elapsed_s': round(time.time() - t0)}), flush=True)
    (a.out / 'manifest.json').write_text(json.dumps({'engine': 'chatterbox', 'model': eng.loaded, 'seed': a.seed,
                                                     'beats': beats}, indent=1), encoding='utf-8')


if __name__ == '__main__':
    main()
