"""Render a spreadsheet lesson: real narration + live spreadsheet recording + captions + QC.

    xvfb-run -a -s "-screen 0 1920x1080x24" python -m scripts.render_lesson \
        --lesson content/expense-tracker-lesson --voice voices/en_US-libritts_r-medium.onnx --output-dir out

    # Offline DRAFT preview (no voice model): estimated timing, silent audio, watermarked.
    xvfb-run -a ... python -m scripts.render_lesson --lesson content/expense-tracker-lesson --draft --output-dir out

Every action declared in lesson.json is performed on the real template while recording, and
each action's ``expect`` values are read back from the live workbook. A mismatch aborts the
render: the video can never show a result that the narration does not describe.
A draft can never be packaged for release (see channel.lesson_release).
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from production_pro.lesson_narration import NarrationResult, cue_time, estimate_narration, narrate_chapters

W, H, FPS = 1920, 1080, 24
NAVY, NAVY2, MINT, AMBER, WHITE, MUTED = '#0B1021', '#14273B', '#7BF1D0', '#F7BF75', '#FFFFFF', '#AEBED8'
FONT_DIRS = ('/usr/share/fonts/opentype/inter/', '/usr/share/fonts/truetype/inter/')
CUE_LEAD_S = 0.15          # act just before the cue word lands


class LessonRenderError(RuntimeError):
    pass


def _font(bold: bool, size: int):
    names = ('InterDisplay-Bold.otf', 'Inter-Bold.otf', 'Inter-Bold.ttf') if bold else \
            ('InterDisplay-Medium.otf', 'Inter-Medium.otf', 'Inter-Regular.ttf')
    for d in FONT_DIRS:
        for n in names:
            if Path(d, n).is_file():
                return ImageFont.truetype(str(Path(d, n)), size)
    fallback = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    return ImageFont.truetype(fallback, size)


def _wrap(draw, text, font, width):
    lines, line = [], ''
    for word in text.split():
        trial = (line + ' ' + word).strip()
        if draw.textlength(trial, font=font) <= width or not line:
            line = trial
        else:
            lines.append(line); line = word
    return lines + ([line] if line else [])


def load_lesson(lesson_dir: Path) -> dict:
    lesson = json.loads((Path(lesson_dir) / 'lesson.json').read_text(encoding='utf-8'))
    if lesson.get('renderer') != 'spreadsheet':
        raise LessonRenderError('Not a spreadsheet lesson')
    if not (Path(lesson_dir) / lesson['template']).is_file():
        raise LessonRenderError('Template missing: ' + lesson['template'])
    for ch in lesson['chapters']:
        if ch.get('visual') not in ('sheet', 'card'):
            raise LessonRenderError('Chapter visual must be sheet or card: ' + ch['title'])
        for a in ch.get('actions', []):
            if a['cue'].lower() not in ch['narration'].lower():
                raise LessonRenderError(f"Cue not spoken in its chapter: {a['cue']!r}")
    return lesson


def build_schedule(lesson: dict, narration: NarrationResult) -> list[tuple[float, dict]]:
    schedule = []
    for ch, t in zip(lesson['chapters'], narration.timeline):
        for a in ch.get('actions', []):
            at = max(0.0, cue_time(narration.words, a['cue'], t['start'], t['end']) - CUE_LEAD_S)
            schedule.append((at, {k: v for k, v in a.items() if k != 'cue'}))
    return sorted(schedule, key=lambda x: x[0])


def check_evidence(log: list[dict]) -> list[dict]:
    rows, failures = [], []
    for entry in log:
        expect = entry['action'].get('expect') or {}
        for ref, want in expect.items():
            got = entry.get('observed', {}).get(ref)
            ok = got == want
            rows.append({'at_s': entry['actual_s'], 'ref': ref, 'expected': want, 'observed': got, 'passed': ok})
            if not ok:
                failures.append(rows[-1])
    if failures:
        raise LessonRenderError('Live spreadsheet did not match the narration: ' + json.dumps(failures))
    return rows


def chapter_band(path: Path, index: int, total: int, title: str, draft: bool):
    """Top band over the app's menu/toolbars: brand, chapter number and title."""
    img = Image.new('RGBA', (W, 84), NAVY + 'F2'); d = ImageDraw.Draw(img)
    d.text((40, 42), 'LOGICSCRIPT', font=_font(True, 26), fill=MINT, anchor='lm')
    d.text((300, 42), f'{index + 1:02d} / {total}', font=_font(True, 26), fill=MUTED, anchor='lm')
    d.text((420, 42), title, font=_font(True, 32), fill=WHITE, anchor='lm')
    if draft:
        d.text((W - 40, 42), 'DRAFT PREVIEW · NO VOICE · ESTIMATED TIMING', font=_font(True, 22), fill=AMBER, anchor='rm')
    img.save(path)


def chapter_card(path: Path, index: int, total: int, title: str, key: str, draft: bool):
    img = Image.new('RGBA', (W, H), NAVY); d = ImageDraw.Draw(img)
    for y in range(H):  # subtle vertical gradient
        d.line([(0, y), (W, y)], fill=(11 + y * 9 // H, 16 + y * 22 // H, 33 + y * 26 // H, 255))
    d.text((130, 140), 'LOGICSCRIPT  /  SPREADSHEETS YOU CAN TRUST', font=_font(True, 26), fill=MINT, anchor='lm')
    y = 260
    for line in _wrap(d, title, _font(True, 76), 1560):
        d.text((130, y), line, font=_font(True, 76), fill=WHITE); y += 96
    y += 40
    key_lines = _wrap(d, key, _font(False, 52), 1500)
    d.rectangle((130, y, 1790, y + 60 + 74 * len(key_lines)), fill=NAVY2)
    d.rectangle((130, y, 140, y + 60 + 74 * len(key_lines)), fill=MINT)
    for i, line in enumerate(key_lines):
        d.text((180, y + 30 + 74 * i), line, font=_font(False, 52), fill=MINT)
    d.text((130, 900), f'{index + 1:02d} / {total}', font=_font(True, 24), fill='#7C91B2')
    if draft:
        d.text((W - 130, 900), 'DRAFT PREVIEW · NO VOICE', font=_font(True, 24), fill=AMBER, anchor='ra')
    img.save(path)


def _ass_filter(ass: Path) -> str:
    sub = str(Path(ass).resolve()).replace('\\', '\\\\').replace(':', '\\:').replace("'", r"\'") \
        .replace('[', r'\[').replace(']', r'\]')
    return "subtitles=filename='" + sub + "'"


def compose(recording, lead_s, narration: NarrationResult, overlays: list[tuple[Path, float, float]],
            audio: Path | None, out: Path, captions: Path | None = None):
    """One encode: trim the recording to the narration clock, add timed overlays (with fades),
    burn the captions (if given) and mux the audio."""
    total = narration.duration_s
    cmd = ['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error', '-ss', f'{lead_s:.3f}', '-t', f'{total:.3f}',
           '-i', str(recording)]
    for png, _, _ in overlays:
        cmd += ['-loop', '1', '-t', f'{total:.3f}', '-i', str(png)]
    if audio is not None:
        cmd += ['-i', str(audio)]
    else:
        cmd += ['-f', 'lavfi', '-t', f'{total:.3f}', '-i', 'anullsrc=channel_layout=mono:sample_rate=48000']
    filters = [f'[0:v]fps={FPS},scale={W}:{H},setsar=1,format=yuv420p[base0]']
    prev = 'base0'
    for i, (_, start, end) in enumerate(overlays, start=1):
        fade_out = max(start, end - 0.25)
        filters.append(f'[{i}:v]format=rgba,fade=t=in:st={start:.3f}:d=0.25:alpha=1,'
                       f'fade=t=out:st={fade_out:.3f}:d=0.25:alpha=1[ov{i}]')
        filters.append(f"[{prev}][ov{i}]overlay=0:0:enable='between(t,{start:.3f},{end:.3f})'[base{i}]")
        prev = f'base{i}'
    if captions is not None:
        filters.append(f'[{prev}]{_ass_filter(captions)}[vout]'); prev = 'vout'
    audio_idx = len(overlays) + 1
    cmd += ['-filter_complex', ';'.join(filters), '-map', f'[{prev}]', '-map', f'{audio_idx}:a',
            '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-r', str(FPS), '-c:a', 'aac', '-b:a', '160k',
            '-ar', '48000', '-t', f'{total:.3f}', '-movflags', '+faststart', str(out)]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode:
        raise LessonRenderError('Compose failed: ' + p.stderr[-800:])
    return out


def run(lesson_dir: Path, out: Path, *, voice: Path | None = None, draft: bool = False,
        narrator=None, aligner=None, recorder_factory=None) -> dict:
    lesson_dir, out = Path(lesson_dir), Path(out)
    lesson = load_lesson(lesson_dir)
    chapters = lesson['chapters']
    out.mkdir(parents=True, exist_ok=True)

    # 1. Narration (real) or clearly-labelled draft timing
    if draft:
        narration = estimate_narration(chapters); audio = None
    else:
        if narrator is None or aligner is None:
            from narration_pro import PiperOrEdgeNarrator, WhisperXAligner
            if voice is None:
                raise LessonRenderError('A Piper voice model is required (or use --draft)')
            narrator = narrator or PiperOrEdgeNarrator(voice, length_scale=1.03, noise_scale=.5, allow_edge_fallback=False)
            aligner = aligner or WhisperXAligner(min_token_coverage=1)
        narration = narrate_chapters(chapters, out, narrator=narrator, aligner=aligner)
        from narration_pro import normalize_loudness
        normalize_loudness(narration.audio_path, out / 'vo_norm.wav'); audio = out / 'vo_norm.wav'

    # 2. Live spreadsheet recording with evidence
    schedule = build_schedule(lesson, narration)
    if recorder_factory is None:
        from production_pro.sheet_recorder import SheetRecorder
        recorder_factory = SheetRecorder
    setup = lesson.get('demo_setup', {})
    with recorder_factory(lesson_dir / lesson['template'], out / 'recording') as rec:
        if setup.get('clear'):
            rec.apply({'do': 'clear', 'ref': setup['clear']}, sleep=lambda s: None)
        for action in setup.get('rows', []):
            rec.apply(action, sleep=lambda s: None)
        if setup.get('start'):
            rec.apply(setup['start'], sleep=lambda s: None)
        recording = rec.record(schedule, narration.duration_s + 0.5, out / 'recording' / 'screen.mp4',
                               evidence_refs=lambda a: list((a.get('expect') or {}).keys()))
    evidence = check_evidence(recording.log)
    (out / 'demo_evidence.json').write_text(json.dumps({'actions': recording.log, 'checks': evidence}, indent=2,
                                                       default=str), encoding='utf-8')
    late = [e for e in recording.log if e['actual_s'] - e['planned_s'] > 0.9]
    if late:
        raise LessonRenderError(f'{len(late)} action(s) ran more than 0.9 s after their cue')

    # 3. Overlays: chapter bands on sheet chapters, full cards on card chapters
    ov_dir = out / 'overlays'; ov_dir.mkdir(exist_ok=True); overlays = []
    for i, (ch, t) in enumerate(zip(chapters, narration.timeline)):
        path = ov_dir / f'{i:02d}.png'
        if ch['visual'] == 'card':
            chapter_card(path, i, len(chapters), ch['title'], ch.get('key', ''), narration.is_draft)
        else:
            chapter_band(path, i, len(chapters), ch['title'], narration.is_draft)
        overlays.append((path, t['start'], t['end']))
    # 4. Captions, then a single encode for the final video; SRT sidecar; QC
    from narration_pro import build_ass_from_words
    from scripts.render_showcase import export_srt
    count, _ = build_ass_from_words(narration.words, out / 'captions.ass', width=W, height=H, animated=True, size=48,
                                    max_chars_per_line=32, max_duration_s=2.8, bottom_margin=65)
    compose(recording.video_path, recording.lead_s, narration, overlays, audio, out / 'final.mp4',
            captions=out / 'captions.ass')
    export_srt(out / 'captions.ass', out / 'captions.srt')
    report = {'title': lesson['title'], 'renderer': 'spreadsheet', 'draft': narration.is_draft,
              'narration_method': narration.method, 'narration_backend': 'none (draft)' if draft else 'piper',
              'caption_count': count, 'alignment_duration_s': narration.duration_s,
              'evidence_checks': len(evidence), 'evidence_passed': all(r['passed'] for r in evidence),
              'resolution': f'{W}x{H}', 'ready_for_publication': False, 'publishing': 'disabled',
              'live_llm_calls': 0, 'editorial_review': 'separate review required', 'chapters': narration.timeline}
    if not draft:
        from production_pro.qc import run_qc
        from scripts.enforce_gates import enforce, measure_loudness
        qc = run_qc(out / 'final.mp4', out / 'captions.ass', min_caption_coverage=.70, forced_alignment_verified=True)
        if not qc.passed:
            raise LessonRenderError('Technical QC failed; inspect the report')
        lufs, peak = measure_loudness(out / 'final.mp4')
        report.update(technical_qc=qc.model_dump(), final_duration_s=qc.duration_s, final_lufs=lufs, final_tp=peak,
                      aligner_ran=True, method='whisperx_ctc')
        (out / 'qc_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        gates = enforce(out, expected_size=(W, H))
        (out / 'independent_gates.json').write_text(json.dumps(gates, indent=2), encoding='utf-8')
    else:
        report['method'] = 'estimated_draft'
        (out / 'qc_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')

    # 5. Companion files: thumbnail, template, script, sources, review frames
    thumb = lesson.get('thumbnail')
    if thumb and (lesson_dir / thumb).is_file():
        shutil.copy2(lesson_dir / thumb, out / 'thumbnail.jpg')
    shutil.copy2(lesson_dir / lesson['template'], out / lesson['template'])
    for name in ('script.md', 'sources.md', 'lesson.json'):
        if (lesson_dir / name).is_file():
            shutil.copy2(lesson_dir / name, out / name)
    frames = out / 'review_frames'; frames.mkdir(exist_ok=True)
    for i, t in enumerate(narration.timeline):
        at = t['start'] + min(6.0, (t['end'] - t['start']) * 0.6)
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-ss', f'{at:.2f}', '-i', str(out / 'final.mp4'),
                        '-frames:v', '1', str(frames / f'{i:02d}.jpg')], check=True)
    return report
