"""One command: prompt (or script, or plan) -> finished, checked MP4.

    python -m studio.make --prompt "Explain what happens after you apply for a job" --out out/job
    python -m studio.make --script-file my_script.txt --style ai-dark --format horizontal --out out/x
    python -m studio.make --plan studio/examples/job_application.json --out out/demo
    add --draft for a silent preview with estimated timing (no voice model needed, never publishable)

Outputs in --out: final.mp4, plan.json (what was shown and why), captions.srt, report.json (every check),
thumbnail.jpg (a frame from the hook), review/ (one frame per shot). Nothing is uploaded or published.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

from .audio import effects_for, estimate, kokoro, mix
from .director import DirectorFailed, Script, direct
from .plan import VideoPlan, spoken
from .render import render_video, snapshot
from .resolve import resolve
from .styles import resolve as resolve_style
from .validate import check_plan


class StudioFailed(RuntimeError):
    pass


def srt(captions: list[dict], path: Path) -> Path:
    def ts(x):
        ms = int(round(x * 1000)); h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); s, ms = divmod(ms, 1000)
        return f'{h:02}:{m:02}:{s:02},{ms:03}'
    path.write_text('\n'.join(f"{i}\n{ts(c['start'])} --> {ts(c['end'])}\n{' '.join(w['text'] for w in c['words'])}\n"
                              for i, c in enumerate(captions, 1)), encoding='utf-8')
    return path


def produce(plan: VideoPlan, out: Path, *, draft: bool = False, voice: str = '', log=print, browser_path=None) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    texts = [spoken(b.narration) for b in plan.beats]
    if draft:
        narration = estimate(texts)
    else:
        log('narration: kokoro')
        narration = kokoro(texts, out / 'voice', language=plan.language, voice=voice or plan.voice)
    res = resolve(plan, narration)
    style = resolve_style(plan.style)
    (out / 'render.json').write_text(json.dumps(res.data, indent=1, ensure_ascii=False), encoding='utf-8')
    audio = out / 'mix.wav'
    mix(audio, res.data['duration'], narration, res.beat_starts, effects_for(res.cues, res.shot_starts),
        'none' if style.get('music') == 'none' else (plan.music or style.get('music', 'soft')))
    log(f"render: {res.data['duration']:.1f}s, {len(res.data['shots'])} shots")
    qa = render_video(res.data, out / 'final.mp4', audio=audio, browser_path=browser_path)
    srt(res.data['captions'], out / 'captions.srt')
    review = snapshot(res.data, [s['start'] + (s['end'] - s['start']) * .7 for s in res.data['shots']], out / 'review',
                      browser_path=browser_path)
    hook = sorted(Path(out / 'review').glob('frame_*.jpg'))
    if hook:
        (out / 'thumbnail.jpg').write_bytes(hook[0].read_bytes())
    probe = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration:stream=codec_type,width,height',
                                       '-of', 'json', str(out / 'final.mp4')], capture_output=True, text=True, check=True).stdout)
    dec = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(out / 'final.mp4'), '-f', 'null', '-'], capture_output=True, text=True)
    loud = subprocess.run(['ffmpeg', '-hide_banner', '-i', str(out / 'final.mp4'), '-af', 'ebur128=peak=true', '-f', 'null', '-'],
                          capture_output=True, text=True).stderr
    lufs = [l for l in loud.splitlines() if l.strip().startswith('I:')]
    checks = {
        'js_errors': not qa['js_errors'],
        'no_blank_frames': qa['blank_frames'] == 0,
        'motion': qa['longest_static_s'] <= float(style.get('max_static_s', 2.8)) + 1.2,
        'inside_frame': max(qa['shot_overflow'] or [0]) <= 0.06,
        'decodes': dec.returncode == 0 and not dec.stderr.strip(),
        'audio_and_video': {s['codec_type'] for s in probe['streams']} == {'audio', 'video'},
        'length_matches': abs(float(probe['format']['duration']) - res.data['duration']) < 0.25,
    }
    report = {'title': plan.title, 'draft': draft, 'narration': narration.backend, 'style': style['name'],
              'format': plan.format, 'duration_s': res.data['duration'], 'shots': len(res.data['shots']),
              'cues': len(res.cues), 'render': qa, 'checks': checks, 'passed': all(checks.values()),
              'loudness': lufs[-1].strip() if lufs else None,
              'mp4_sha256': hashlib.sha256((out / 'final.mp4').read_bytes()).hexdigest(),
              'publishable': False, 'note': 'Owner review required. Drafts are never publishable.'}
    (out / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    if not report['passed']:
        raise StudioFailed('final video failed checks: ' + ', '.join(k for k, v in checks.items() if not v))
    return report


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog='python -m studio.make')
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument('--prompt'); src.add_argument('--script-file', type=Path); src.add_argument('--plan', type=Path)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--format', default='vertical', choices=['vertical', 'horizontal', 'square'])
    ap.add_argument('--style', default='auto'); ap.add_argument('--language', default='en')
    ap.add_argument('--seconds', type=int, default=45); ap.add_argument('--voice', default='')
    ap.add_argument('--brand', default='@logicscript'); ap.add_argument('--title', default='')
    ap.add_argument('--draft', action='store_true')
    a = ap.parse_args(argv)
    a.out.mkdir(parents=True, exist_ok=True)
    if a.plan:
        raw = json.loads(a.plan.read_text())
        if a.style != 'auto':
            raw['style'] = a.style
        raw['format'] = a.format if a.format != 'vertical' or 'format' not in raw else raw['format']
        plan, problems = check_plan(raw, work=a.out / 'check')
        if problems:
            print(json.dumps({'passed': False, 'problems': problems}, indent=2)); return 2
        director_report = {'source': 'plan file'}
    else:
        script = None
        if a.script_file:
            paras = [p.strip() for p in a.script_file.read_text(encoding='utf-8').split('\n') if p.strip()]
            script = Script(title=a.title or paras[0][:80], style=a.style if a.style != 'auto' else 'explainer-dark',
                            beats=paras)
        try:
            plan, director_report = direct(a.prompt or '', fmt=a.format, language=a.language, seconds=a.seconds,
                                           style=a.style, brand=a.brand, script=script, work=a.out / 'check')
        except DirectorFailed as e:
            (a.out / 'director.json').write_text(json.dumps(e.report, indent=2), encoding='utf-8')
            print(str(e)); return 3
    (a.out / 'plan.json').write_text(plan.model_dump_json(indent=1), encoding='utf-8')
    (a.out / 'director.json').write_text(json.dumps(director_report, indent=2, default=str), encoding='utf-8')
    try:
        rep = produce(plan, a.out, draft=a.draft, voice=a.voice)
    except StudioFailed as e:
        print(str(e)); return 4
    print(json.dumps({k: rep[k] for k in ('title', 'duration_s', 'shots', 'cues', 'passed', 'narration', 'draft')}, indent=2))
    return 0


def _redact(text: str) -> str:
    import os
    for k, v in os.environ.items():
        if v and len(v) > 8 and any(w in k for w in ('KEY', 'TOKEN', 'SECRET')):
            text = text.replace(v, '***')
    return text


def run(argv=None) -> int:
    """main() with a written record of any crash (error.json next to the outputs) and a CI annotation."""
    import os
    import traceback
    try:
        return main(argv)
    except Exception as exc:  # noqa: BLE001 - report every failure, never silently
        ap = argparse.ArgumentParser(add_help=False); ap.add_argument('--out', type=Path)
        out = ap.parse_known_args(argv)[0].out
        info = {'error': _redact(f'{type(exc).__name__}: {exc}'), 'traceback': _redact(traceback.format_exc())}
        if out:
            out.mkdir(parents=True, exist_ok=True)
            (out / 'error.json').write_text(json.dumps(info, indent=2), encoding='utf-8')
        print(info['traceback'], file=sys.stderr)
        if os.environ.get('GITHUB_ACTIONS'):
            print(f"::error title=studio {out}::{info['error'][:900]}".replace('\n', ' '))
        return 1


if __name__ == '__main__':
    sys.exit(run())
