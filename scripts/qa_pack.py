"""Review pack for a finished preview: frames, audio levels and a speech round-trip.

Produces evidence for a human (and Claude) to inspect; it does not approve
anything. Contact sheets let a reviewer see every part of the video; the
ASR round-trip transcribes the final audio with a separate model and
compares it to the script, which catches skipped or garbled narration.
"""
from __future__ import annotations
import argparse
import json
import re
import subprocess
import unicodedata
from pathlib import Path


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True)


def duration(path: Path) -> float:
    out = _run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(path)])
    return float(out.stdout.strip() or 0)


def contact_sheet(video: Path, out: Path, *, every_s: float, width: int, cols: int, rows: int, offset_s: float = 0.0) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    vf = (f"fps=1/{every_s},scale={width}:-2,"
          f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
          f"text='%{{pts\\:hms\\:{offset_s:.2f}}}':x=6:y=6:fontsize=18:fontcolor=white:box=1:boxcolor=black@0.6,"
          f"tile={cols}x{rows}:padding=4:margin=4")
    proc = _run(['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error', '-i', str(video), '-vf', vf,
                 '-frames:v', '1', '-q:v', '4', str(out)])
    if proc.returncode:
        raise RuntimeError('contact sheet failed: ' + proc.stderr[-300:])
    return out


def contact_sheets(video: Path, out_dir: Path, stem: str, *, every_s: float, width: int, cols: int, rows: int) -> list[str]:
    """Several sheets so every sample of a long video is covered."""
    total = duration(video)
    per_sheet = every_s * cols * rows
    sheets = []
    start, i = 0.0, 0
    while start < total:
        part = out_dir / f'{stem}_part{i}.mp4'
        _run(['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error', '-ss', f'{start:.2f}', '-t', f'{per_sheet:.2f}',
              '-i', str(video), '-an', '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '30', str(part)])
        sheets.append(str(contact_sheet(part, out_dir / f'{stem}_sheet{i}.jpg', every_s=every_s, width=width,
                                        cols=cols, rows=rows, offset_s=start)))
        part.unlink(missing_ok=True)
        start += per_sheet
        i += 1
    return sheets


def audio_levels(video: Path) -> dict:
    loud = _run(['ffmpeg', '-hide_banner', '-nostats', '-i', str(video), '-af', 'ebur128=peak=true', '-f', 'null', '-'])
    text = loud.stderr
    integrated = re.findall(r'I:\s+(-?[\d.]+) LUFS', text)
    peak = re.findall(r'Peak:\s+(-?[\d.]+) dBFS', text)
    silence = _run(['ffmpeg', '-hide_banner', '-nostats', '-i', str(video), '-af', 'silencedetect=n=-45dB:d=1.5',
                    '-f', 'null', '-']).stderr
    gaps = [float(x) for x in re.findall(r'silence_duration: ([\d.]+)', silence)]
    black = _run(['ffmpeg', '-hide_banner', '-nostats', '-i', str(video), '-vf', 'blackdetect=d=0.5:pix_th=0.10',
                  '-an', '-f', 'null', '-']).stderr
    blacks = re.findall(r'black_duration:([\d.]+)', black)
    return {'integrated_lufs': float(integrated[-1]) if integrated else None,
            'true_peak_dbfs': float(peak[-1]) if peak else None,
            'silences_over_1_5s': len(gaps), 'longest_silence_s': max(gaps) if gaps else 0.0,
            'black_segments': len(blacks)}


def _norm_words(text: str) -> list[str]:
    text = unicodedata.normalize('NFKD', text.casefold())
    text = ''.join(c for c in text if not unicodedata.combining(c))
    return re.findall(r"[a-z0-9]+", text)


def word_error_rate(reference: str, hypothesis: str) -> float:
    ref, hyp = _norm_words(reference), _norm_words(hypothesis)
    if not ref:
        return 1.0
    prev = list(range(len(hyp) + 1))
    for i, r in enumerate(ref, 1):
        cur = [i] + [0] * len(hyp)
        for j, h in enumerate(hyp, 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (r != h))
        prev = cur
    return prev[-1] / len(ref)


def asr_round_trip(video: Path, script_text: str, language: str, out_dir: Path) -> dict:
    try:
        import whisperx  # faster-whisper backend, already installed for alignment
    except ImportError:
        return {'available': False}
    wav = out_dir / 'audio16k.wav'
    _run(['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error', '-i', str(video), '-ac', '1', '-ar', '16000', str(wav)])
    model = whisperx.load_model('small', 'cpu', compute_type='int8', language=language)
    result = model.transcribe(whisperx.load_audio(str(wav)), batch_size=4, language=language)
    heard = ' '.join(seg.get('text', '') for seg in result.get('segments', []))
    (out_dir / 'asr_transcript.txt').write_text(heard, encoding='utf-8')
    wav.unlink(missing_ok=True)
    return {'available': True, 'model': 'whisper-small (independent of the WhisperX aligner model)',
            'wer_vs_script': round(word_error_rate(script_text, heard), 4),
            'script_words': len(_norm_words(script_text)), 'heard_words': len(_norm_words(heard))}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--video', type=Path, required=True)
    ap.add_argument('--script', type=Path, required=True)
    ap.add_argument('--shorts', type=Path)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--no-asr', action='store_true')
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    script = json.loads(args.script.read_text(encoding='utf-8'))
    text = ' '.join([script['hook'], *[s['narration'] for s in script['sections']], script['cta']])
    report = {'video': {'duration_s': round(duration(args.video), 2), **audio_levels(args.video),
                        'sheets': contact_sheets(args.video, args.out, 'long', every_s=12, width=384, cols=5, rows=6)}}
    if not args.no_asr:
        report['video']['asr'] = asr_round_trip(args.video, text, script.get('language', 'en'), args.out)
    report['shorts'] = []
    if args.shorts and args.shorts.is_dir():
        for short in sorted(args.shorts.glob('short_*.mp4')):
            report['shorts'].append({'file': short.name, 'duration_s': round(duration(short), 2),
                                     **audio_levels(short),
                                     'sheets': contact_sheets(short, args.out, short.stem, every_s=4, width=216,
                                                              cols=7, rows=2)})
    (args.out / 'qa_report.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
