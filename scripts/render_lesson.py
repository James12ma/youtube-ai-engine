"""Render any lesson by its lesson.json "renderer" field.

    python -m scripts.render_lesson --lesson content/expense-rule-lesson --voice <piper.onnx> --output-dir out
    xvfb-run -a -s "-screen 0 1920x1080x24" python -m scripts.render_lesson \
        --lesson content/expense-tracker-lesson --voice <piper.onnx> --output-dir out
    xvfb-run -a ... python -m scripts.render_lesson --lesson content/expense-tracker-lesson --draft --output-dir out

Renderers:
  browser-app  -> scripts.render_educational  (records a local web app; the One-Cent lesson)
  spreadsheet  -> scripts.render_spreadsheet_lesson  (records the real template in LibreOffice)
No renderer uploads or publishes.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

RENDERERS = ('browser-app', 'spreadsheet')


def renderer_for(lesson_dir: Path) -> str:
    data = json.loads((Path(lesson_dir) / 'lesson.json').read_text(encoding='utf-8'))
    kind = data.get('renderer', 'browser-app')
    if kind not in RENDERERS:
        raise ValueError(f'Unknown renderer {kind!r}; expected one of {RENDERERS}')
    return kind


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog='python -m scripts.render_lesson')
    p.add_argument('--lesson', type=Path, required=True)
    p.add_argument('--voice', type=Path)
    p.add_argument('--output-dir', type=Path, required=True)
    p.add_argument('--draft', action='store_true', help='Offline preview: no voice, estimated timing (spreadsheet only)')
    p.add_argument('--reuse-narration', type=Path, help='browser-app only: reuse verified narration')
    args = p.parse_args(argv)
    kind = renderer_for(args.lesson)
    if kind == 'browser-app':
        if args.draft:
            raise SystemExit('--draft is only supported for spreadsheet lessons')
        from scripts.render_educational import run
        run(args.voice, args.output_dir, args.reuse_narration, args.lesson)
        print(json.dumps({'renderer': kind, 'output': str(args.output_dir)}))
    else:
        from scripts.render_spreadsheet_lesson import run
        report = run(args.lesson, args.output_dir, voice=args.voice, draft=args.draft)
        print(json.dumps({'renderer': kind, 'draft': report['draft'], 'chapters': len(report['chapters']),
                          'evidence_checks': report['evidence_checks'], 'output': str(args.output_dir)}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
