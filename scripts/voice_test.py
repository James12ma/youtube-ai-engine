"""Compare free Piper voices on hard Spanish words, judged by two independent ASR models.

Writes one WAV per voice plus results.json. Nothing is published.
"""
from __future__ import annotations
import argparse
import json
import re
import unicodedata
import wave
from pathlib import Path

SENTENCES = [
    'Viajan entre las aguas frías donde se alimentan y las aguas cálidas donde nacen sus crías.',
    'Una madre nada junto a su cría. La cría seguirá cerca de ella hasta un año.',
    'En Hawái, otra ballena mantiene la cola fuera del agua.',
]
TARGETS = ['frías', 'crías', 'cría', 'año', 'hawái']


def _norm(t: str) -> str:
    t = unicodedata.normalize('NFKD', t.casefold())
    return ''.join(c for c in t if not unicodedata.combining(c))


def hits(text: str) -> dict:
    words = re.findall(r'[a-z]+', _norm(text))
    return {w: words.count(_norm(w)) for w in TARGETS}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--voices-dir', type=Path, required=True)
    ap.add_argument('--voices', required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    from piper import PiperVoice, SynthesisConfig
    import whisperx
    args.out.mkdir(parents=True, exist_ok=True)
    text = ' '.join(SENTENCES)
    expected = hits(text)
    variants = []
    for v in args.voices.split(','):
        variants.append((v, v, text))
    # Phonetic variant for the current voice: explicit IPA for the two words, same meaning/spelling on screen.
    variants.append(('es_MX-claude-high+ipa', 'es_MX-claude-high',
                     text.replace('frías', '[[ fɾˈias ]]').replace('crías', '[[ kɾˈias ]]')
                         .replace('cría', '[[ kɾˈia ]]')))
    asr = {m: whisperx.load_model(m, 'cpu', compute_type='int8', language='es') for m in ('small', 'medium')}
    results = []
    for name, voice_name, spoken in variants:
        model = args.voices_dir / f'{voice_name}.onnx'
        if not model.is_file():
            results.append({'voice': name, 'error': 'voice not downloaded'}); continue
        voice = PiperVoice.load(str(model), config_path=str(model) + '.json', use_cuda=False)
        wav = args.out / f'{name}.wav'
        try:
            with wave.open(str(wav), 'wb') as fh:
                voice.synthesize_wav(spoken, fh, syn_config=SynthesisConfig())
        except Exception as exc:  # e.g. IPA syntax unsupported
            results.append({'voice': name, 'error': type(exc).__name__ + ': ' + str(exc)[:200]}); continue
        row = {'voice': name}
        for m, model_asr in asr.items():
            res = model_asr.transcribe(whisperx.load_audio(str(wav)), batch_size=4, language='es')
            heard = ' '.join(s.get('text', '') for s in res.get('segments', []))
            got = hits(heard)
            row[m] = {'heard': heard.strip(), 'target_hits': f'{sum(min(got[w], expected[w]) for w in TARGETS)}/{sum(expected.values())}'}
        results.append(row)
    (args.out / 'results.json').write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(results, ensure_ascii=False))


if __name__ == '__main__':
    main()
