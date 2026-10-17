"""Three narrator candidates on the SAME Spanish text, plus the current voice for reference.

  python -m scripts.voice_compare synth --engine piper-current|piper-plus|kokoro|chatterbox --out X.wav
  python -m scripts.voice_compare analyze --dir D        (ASR round-trip + prosody numbers)
Nothing is published; the workflow sends the audio only to the owner's Telegram.
"""
from __future__ import annotations
import argparse
import json
import os
import re
import unicodedata
from pathlib import Path

TEXT = """Bajo el agua, algo enorme se acerca. Primero es solo una sombra… luego, una aleta blanca, larguísima.

Es una ballena jorobada. Y no está sola.

A su lado nada su cría, nacida hace apenas unas semanas en estas aguas cálidas del Caribe. Cada pocos minutos, la pequeña sube a respirar… y vuelve, siempre, junto a su madre.

¿Cuánto tiempo pasarán juntas? Casi un año. Y en ese tiempo, la cría aprenderá todo lo que necesita para cruzar un océano entero."""


def synth(engine: str, out: Path, ref: Path | None) -> dict:
    from channel import voices
    vdir = Path(os.environ.get('VOICE_DIR', 'voices'))
    if engine == 'piper-current':      # exactly what the pipeline does today: one block, default noise
        e = voices.PiperEngine(vdir / 'es_MX-claude-high.onnx', length_scale=1.1)
        return voices.narrate(e, TEXT, out, sentence_level=False)
    if engine == 'piper-plus':         # same voice, story rhythm + more natural variation
        e = voices.PiperEngine(vdir / 'es_MX-claude-high.onnx', length_scale=1.05, noise_scale=0.8, noise_w=1.0)
        return voices.narrate(e, TEXT, out)
    if engine == 'kokoro':
        return voices.narrate(voices.KokoroEngine(os.environ.get('KOKORO_VOICE', 'em_alex'), speed=0.95), TEXT, out)
    if engine == 'chatterbox':
        e = voices.ChatterboxEngine(ref, latam=True, exaggeration=float(os.environ.get('CB_EXAG', '0.6')),
                                    cfg_weight=float(os.environ.get('CB_CFG', '0.4')))
        r = voices.narrate(e, TEXT, out)
        r['model'] = e.loaded
        return r
    raise SystemExit('unknown engine ' + engine)


def _norm(t: str) -> list[str]:
    t = unicodedata.normalize('NFKD', t.casefold())
    return re.findall(r'[a-z]+', ''.join(c for c in t if not unicodedata.combining(c)))


def wer(ref: str, hyp: str) -> float:
    r, h = _norm(ref), _norm(hyp)
    d = list(range(len(h) + 1))
    for i in range(1, len(r) + 1):
        prev, d[0] = d[0], i
        for j in range(1, len(h) + 1):
            cur = d[j]
            d[j] = min(d[j] + 1, d[j - 1] + 1, prev + (r[i - 1] != h[j - 1]))
            prev = cur
    return round(d[len(h)] / max(1, len(r)), 3)


def analyze(folder: Path) -> list[dict]:
    import whisperx
    from channel.voices import prosody
    asr = whisperx.load_model('small', 'cpu', compute_type='int8', language='es')
    rows = []
    for wav in sorted(folder.glob('*.wav')):
        audio = whisperx.load_audio(str(wav))
        heard = ' '.join(s['text'] for s in asr.transcribe(audio, batch_size=4, language='es')['segments'])
        rows.append({'sample': wav.stem, 'wer': wer(TEXT, heard), **prosody(wav), 'heard': heard[:400]})
    (folder / 'analysis.json').write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding='utf-8')
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('synth'); s.add_argument('--engine', required=True); s.add_argument('--out', type=Path, required=True)
    s.add_argument('--ref', type=Path)
    a = sub.add_parser('analyze'); a.add_argument('--dir', type=Path, required=True)
    args = ap.parse_args()
    if args.cmd == 'synth':
        r = synth(args.engine, args.out, args.ref)
        r.pop('sentences', None)
        print(json.dumps(r, ensure_ascii=False))
    else:
        for r in analyze(args.dir):
            print(json.dumps({k: v for k, v in r.items() if k != 'heard'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
