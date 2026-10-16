"""Turn one AI clip (e.g. made in the Gemini app) into a finished, private Alan7 short.

Spanish narration from the caption (Piper), forced-aligned subtitles, the permanent
"Recreación generada con IA" label, credits. Native resolution only: the clip is never upscaled.
"""
from __future__ import annotations
import argparse
import json
import subprocess
from pathlib import Path
from channel.documentary import DocumentaryPlan, DocumentaryError, render_documentary

PRONUNCIATIONS = {'frías': 'fɾˈias', 'crías': 'kɾˈias', 'cría': 'kɾˈia'}


def probe(path: Path) -> tuple[float, int, int]:
    out = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
                          'stream=width,height:format=duration', '-of', 'json', str(path)],
                         capture_output=True, text=True, check=True).stdout
    j = json.loads(out)
    return float(j['format']['duration']), int(j['streams'][0]['width']), int(j['streams'][0]['height'])


def build_plan(clip: Path, caption: str, duration: float) -> DocumentaryPlan:
    return DocumentaryPlan.model_validate({
        'series': 'Historias Salvajes', 'title': 'Clip', 'language': 'es', 'show_title': False,
        'preroll_s': 0.6, 'pause_s': 0.0, 'tail_s': 0.6, 'credits_s': 3.0, 'crossfade_s': 0.4,
        'pronunciations': PRONUNCIATIONS,
        'clips': {'gen': {'kind': 'ai', 'path': str(clip), 'ai_generated': True}},
        'beats': [{'narration': caption, 'shots': [{'clip': 'gen', 'in_s': 0.0, 'out_s': max(1.6, duration - 0.05),
                                                    'label': ''}]}],
        'credits_note': 'Narración: voz sintética Piper (es_MX). Imágenes: recreación generada con IA. Muestra privada de Alan7 — no publicada.',
    })


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--clip', type=Path, required=True)
    ap.add_argument('--caption', required=True)
    ap.add_argument('--voice-model', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    duration, w, h = probe(a.clip)
    # keep native size (even dimensions for x264); never scale up
    w, h = w - w % 2, h - h % 2
    plan = build_plan(a.clip, ' '.join(a.caption.split()), duration)
    try:
        report = render_documentary(plan, a.voice_model, a.out, width=w, height=h)
    except DocumentaryError as e:
        msg = str(e)
        if 'shots only hold' in msg or 'window too short' in msg:
            msg = f'la narración es más larga que el clip ({duration:.1f} s); acorta el texto'
        raise SystemExit('ERROR: ' + msg)
    print(json.dumps({'duration_s': report['duration_s'], 'size': f'{w}x{h}', 'captions': report['captions']}))


if __name__ == '__main__':
    main()
