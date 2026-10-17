"""Shared narrator for Alan7 AND LogicScript: the owner-approved voice (Chatterbox, Oct 2026).

Runs inside the Chatterbox virtualenv (see .github/actions/alan7-voice). Input is either a documentary
plan (--plan: one text per beat) or a JSON list of texts (--texts). Output: seg_<i>.wav (24 kHz mono)
+ manifest.json with a text hash per segment, so a renderer can refuse audio that does not match.

Timbre: a SYNTHETIC reference clip (Kokoro em_alex, first 12 s of the approved sample text) — never a
real person's voice. Spanish uses the Latin-American fine-tune; English uses the multilingual V3 model.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import time
from pathlib import Path

from scripts.voice_compare import _voices


def text_key(text: str) -> str:
    return hashlib.sha1(' '.join(text.split()).encode()).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--plan', type=Path)
    ap.add_argument('--texts', type=Path, help='JSON list of strings')
    ap.add_argument('--language', default='es', choices=['es', 'en'])
    ap.add_argument('--ref', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--seed', type=int, default=7)
    a = ap.parse_args()
    exag, cfg = 0.6, (0.4 if a.language == 'es' else 0.3)
    if a.plan:
        plan = json.loads(a.plan.read_text(encoding='utf-8'))
        texts = [b['narration'] for b in plan['beats']]
        exag, cfg = float(plan.get('voice_exaggeration', exag)), float(plan.get('voice_cfg', cfg))
        a.language = plan.get('language', a.language)
    else:
        texts = json.loads(a.texts.read_text(encoding='utf-8'))
    v = _voices()
    # English: Chatterbox multilingual V3 (sample C, Oct 2026: 1.7 % ASR error vs 6.9 % for the English-only model,
    # and more pitch variation) with the same synthetic reference -> same timbre as Alan7.
    eng = v.ChatterboxEngine(a.ref, latam=a.language == 'es', language=a.language,
                             english_model=False, exaggeration=exag, cfg_weight=cfg, seed=a.seed)
    checker = v.SpeechChecker(a.language)   # pronunciation check: misheard sentences are generated again
    a.out.mkdir(parents=True, exist_ok=True)
    items, t0 = [], time.time()
    report = []
    for i, text in enumerate(texts):
        text = ' '.join(text.split())
        f = f'seg_{i:03d}.wav'
        r = v.narrate(eng, text, a.out / f, checker=checker)
        left = [m for x in r['sentences'] for m in x.get('misheard', [])]
        retried = sum(1 for x in r['sentences'] if x.get('tries', 1) > 1)
        items.append({'index': i, 'sha1': text_key(text), 'file': f, 'seconds': r['seconds'],
                      'retried_sentences': retried, 'misheard_left': left})
        report.append(r['sentences'])
        print(json.dumps({'segment': i, 'seconds': r['seconds'], 'elapsed_s': round(time.time() - t0)}), flush=True)
    (a.out / 'manifest.json').write_text(json.dumps({
        'engine': 'chatterbox', 'model': eng.loaded, 'language': a.language, 'seed': a.seed,
        'exaggeration': exag, 'cfg_weight': cfg, 'beats': items}, indent=1, ensure_ascii=False), encoding='utf-8')
    (a.out / 'pronunciation.json').write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding='utf-8')


if __name__ == '__main__':
    main()
