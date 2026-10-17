"""Opt-in common mastering without modifying Alan7's documentary renderer.

Existing render commands remain valid. This command renders with them first,
then applies the same audio/encoding contract; it never uploads or approves.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

from production_pro.premium import QualityProfile, master_video, audit_video


def master_documentary(plan, voice_model: Path, out: Path, **assets) -> dict:
    from channel.documentary import render_documentary
    profile = QualityProfile('documentary', plan.language)
    base = out.with_name(out.stem+'_base.mp4')
    rendered = render_documentary(plan, voice_model, base, width=profile.width,
                                  height=profile.height, fps=profile.fps, **assets)
    work = base.parent / (base.stem+'_work')
    # Reuse the original edit and its actual full-length mixed track. No recut,
    # no monkeypatch, no re-synthesis, and no change to documentary.py/voices.py.
    mastered = master_video(work/'titled.mp4', work/'mix.wav', out,
                             profile=profile, captions=work/'captions.ass')
    return {'original_render': rendered, 'mastering': mastered,
            'mode_checks': audit_video(out, profile=profile, documentary_report=rendered)}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--lesson', type=Path, required=True)
    p.add_argument('--voice', type=Path, required=True)
    p.add_argument('--output-dir', type=Path, required=True)
    args = p.parse_args(argv)
    from scripts.render_lesson import renderer_for
    kind = renderer_for(args.lesson)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    if kind == 'spreadsheet':
        from scripts.render_spreadsheet_lesson import run
        result = run(args.lesson, args.output_dir/'base', voice=args.voice)
    else:
        from scripts.render_educational import run
        run(args.voice, args.output_dir/'base', lesson_dir=args.lesson)
        result = json.loads((args.output_dir/'base'/'qc_report.json').read_text())
    profile = QualityProfile('screen', 'en')
    mastered = master_video(args.output_dir/'base'/'final.mp4', args.output_dir/'base'/'vo_norm.wav',
                             args.output_dir/'final.mp4', profile=profile)
    report = {'original_render': result, 'mastering': mastered, 'ready_for_publication': False}
    (args.output_dir/'premium_report.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
