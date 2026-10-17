"""Offline tests: multi-lesson rendering, shared narration, spreadsheet recorder, video-1 lesson."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import wave
from pathlib import Path

import pytest

from narration_pro.aligner import WordTimestamp
from production_pro.lesson_narration import cue_time, estimate_narration, narrate_chapters
from scripts.render_lesson import renderer_for
from scripts.render_spreadsheet_lesson import (LessonRenderError, build_schedule, chapter_band, chapter_card,
                                               check_evidence, compose, load_lesson)

VIDEO1 = Path('content/expense-tracker-lesson')
ONECENT = Path('content/expense-rule-lesson')


# ---------------- dispatcher / lesson files ----------------

def test_dispatcher_routes_both_lessons():
    assert renderer_for(VIDEO1) == 'spreadsheet'
    assert renderer_for(ONECENT) == 'browser-app'


def test_dispatcher_rejects_unknown_renderer(tmp_path):
    (tmp_path / 'lesson.json').write_text(json.dumps({'renderer': 'hologram', 'chapters': []}))
    with pytest.raises(ValueError, match='Unknown renderer'):
        renderer_for(tmp_path)


def test_one_cent_lesson_preserved_except_renderer_tag():
    data = json.loads((ONECENT / 'lesson.json').read_text())
    assert data['title'] == 'Before You Automate: Test the One-Cent Boundary'
    assert len(data['chapters']) == 18 and data['renderer'] == 'browser-app'


def test_video1_lesson_is_complete_and_consistent():
    lesson = load_lesson(VIDEO1)
    chapters = lesson['chapters']
    assert lesson['title'] == 'Build a Free Expense Tracker That Catches Its Own Mistakes'
    assert len(chapters) == 11
    words = sum(len(c['narration'].split()) for c in chapters)
    assert 950 <= words <= 1800
    expects = [(ref, v) for c in chapters for a in c['actions'] for ref, v in a.get('expect', {}).items()]
    assert len(expects) >= 30
    assert {ref.split('!')[0] for ref, _ in expects} <= {'Expenses', 'Summary', 'Settings'}
    assert (VIDEO1 / lesson['template']).is_file() and (VIDEO1 / lesson['thumbnail']).is_file()
    # narration safety: no deductibility or savings promises
    text = ' '.join(c['narration'] for c in chapters).lower()
    for banned in ('deductible', 'write off', 'write-off', 'save you money', 'guaranteed', 'irs requires'):
        assert banned not in text, banned
    assert 'not tax advice' in text and 'not legal thresholds' in text


def test_load_lesson_rejects_unspoken_cue(tmp_path):
    shutil.copytree(VIDEO1, tmp_path / 'l')
    data = json.loads((tmp_path / 'l' / 'lesson.json').read_text())
    data['chapters'][0]['actions'][0]['cue'] = 'words never spoken here'
    (tmp_path / 'l' / 'lesson.json').write_text(json.dumps(data))
    with pytest.raises(LessonRenderError, match='Cue not spoken'):
        load_lesson(tmp_path / 'l')


def test_load_lesson_rejects_browser_lesson():
    with pytest.raises(LessonRenderError, match='Not a spreadsheet lesson'):
        load_lesson(ONECENT)


# ---------------- narration ----------------

def test_estimated_narration_is_contiguous_and_marked_draft():
    chapters = load_lesson(VIDEO1)['chapters']
    n = estimate_narration(chapters)
    assert n.is_draft and n.method == 'estimated_draft' and n.audio_path is None
    assert n.timeline[0]['start'] == 0
    for a, b in zip(n.timeline, n.timeline[1:]):
        assert a['end'] == pytest.approx(b['start'])
    starts = [w.start_s for w in n.words]
    assert starts == sorted(starts) and n.duration_s == pytest.approx(n.timeline[-1]['end'])
    assert 300 < n.duration_s < 720    # roughly 5-12 minutes


def _wav(path: Path, seconds: float):
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(22050)
        w.writeframes(b'\x00\x00' * int(22050 * seconds))


def test_real_narration_path_offsets_words_and_concatenates(tmp_path):
    class FakeNarrator:
        def synthesize(self, text, path):
            _wav(path, len(text.split()) * 0.4)

    class FakeAligner:
        def align(self, path, text):
            ws = [WordTimestamp(word=t, start_s=i * 0.4, end_s=i * 0.4 + 0.3) for i, t in enumerate(text.split())]
            return type('A', (), {'words': ws, 'duration_s': len(ws) * 0.4})()

    chapters = [{'title': 'One', 'narration': 'alpha beta gamma'}, {'title': 'Two', 'narration': 'delta epsilon'}]
    n = narrate_chapters(chapters, tmp_path, narrator=FakeNarrator(), aligner=FakeAligner())
    assert not n.is_draft and n.method == 'whisperx_ctc'
    assert n.timeline == [{'title': 'One', 'start': 0.0, 'end': pytest.approx(1.2)},
                          {'title': 'Two', 'start': pytest.approx(1.2), 'end': pytest.approx(2.0)}]
    assert n.words[3].word == 'delta' and n.words[3].start_s == pytest.approx(1.2)
    with wave.open(str(n.audio_path)) as w:
        assert w.getnframes() / w.getframerate() == pytest.approx(2.0, abs=0.01)


def test_cue_time_finds_phrase_only_inside_its_chapter():
    words = [WordTimestamp(word=w, start_s=i, end_s=i + 0.5) for i, w in enumerate('look here now look here again'.split())]
    assert cue_time(words, 'look here', 0, 3) == 0
    assert cue_time(words, 'look here', 3, 6) == 3
    with pytest.raises(ValueError):
        cue_time(words, 'not present', 0, 6)


def test_schedule_is_ordered_and_covers_every_action():
    lesson = load_lesson(VIDEO1)
    n = estimate_narration(lesson['chapters'])
    schedule = build_schedule(lesson, n)
    total = sum(len(c['actions']) for c in lesson['chapters'])
    assert len(schedule) == total
    times = [t for t, _ in schedule]
    assert times == sorted(times) and all(0 <= t < n.duration_s for t in times)
    assert all('cue' not in a for _, a in schedule)


# ---------------- evidence gate ----------------

def test_evidence_gate_passes_and_fails():
    good = [{'actual_s': 1.0, 'action': {'expect': {'Expenses!J9': 'ERROR'}}, 'observed': {'Expenses!J9': 'ERROR'}}]
    assert check_evidence(good)[0]['passed'] is True
    bad = [{'actual_s': 1.0, 'action': {'expect': {'Expenses!J9': 'ERROR'}}, 'observed': {'Expenses!J9': 'OK'}}]
    with pytest.raises(LessonRenderError, match='did not match the narration'):
        check_evidence(bad)


# ---------------- overlays / compose ----------------

def test_overlay_images_and_compose(tmp_path):
    band, card = tmp_path / 'b.png', tmp_path / 'c.png'
    chapter_band(band, 0, 11, 'Rule one: dates you can trust', draft=True)
    chapter_card(card, 9, 11, 'Your weekly routine', 'Enter → fix ERRORs → review CHECKs', draft=False)
    from PIL import Image
    assert Image.open(band).size == (1920, 84) and Image.open(card).size == (1920, 1080)
    rec = tmp_path / 'rec.mp4'
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'lavfi', '-i', 'color=c=white:s=1920x1080:d=6:r=24',
                    '-c:v', 'libx264', '-preset', 'ultrafast', str(rec)], check=True)
    narration = type('N', (), {'duration_s': 4.0})()
    out = compose(rec, 1.0, narration, [(band, 0.0, 2.0), (card, 2.0, 4.0)], None, tmp_path / 'out.mp4')
    probe = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration:stream=codec_type',
                                       '-of', 'json', str(out)], capture_output=True, text=True).stdout)
    assert {s['codec_type'] for s in probe['streams']} == {'video', 'audio'}
    assert float(probe['format']['duration']) == pytest.approx(4.0, abs=0.15)


def test_compose_burns_captions_in_the_same_encode(tmp_path):
    from narration_pro import build_ass_from_words
    words = [WordTimestamp(word=w, start_s=i * 0.5, end_s=i * 0.5 + 0.4) for i, w in enumerate('one two three four'.split())]
    build_ass_from_words(words, tmp_path / 'c.ass', width=1920, height=1080, animated=True, size=48,
                         max_chars_per_line=32, max_duration_s=2.8, bottom_margin=65)
    rec = tmp_path / 'rec.mp4'
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'lavfi', '-i', 'color=c=black:s=1920x1080:d=4:r=24',
                    '-c:v', 'libx264', '-preset', 'ultrafast', str(rec)], check=True)
    narration = type('N', (), {'duration_s': 2.5})()
    plain = compose(rec, 0.5, narration, [], None, tmp_path / 'plain.mp4')
    burned = compose(rec, 0.5, narration, [], None, tmp_path / 'burned.mp4', captions=tmp_path / 'c.ass')
    def frame_mean(path):
        raw = subprocess.run(['ffmpeg', '-loglevel', 'error', '-ss', '1.2', '-i', str(path), '-frames:v', '1',
                              '-f', 'rawvideo', '-pix_fmt', 'gray', '-'], capture_output=True).stdout
        return sum(raw) / len(raw)
    assert frame_mean(burned) > frame_mean(plain) + 0.05   # caption pixels present only when burned


# ---------------- live LibreOffice (runs when soffice + xvfb-run exist) ----------------

LIVE = shutil.which('soffice') and shutil.which('xvfb-run')


@pytest.mark.skipif(not LIVE, reason='LibreOffice/Xvfb not installed')
def test_live_recorder_reproduces_the_hook_and_fix(tmp_path):
    script = tmp_path / 'live.py'
    script.write_text(f'''
import json, sys
sys.path.insert(0, {str(Path.cwd())!r})
from pathlib import Path
from production_pro.sheet_recorder import SheetRecorder
lesson = json.loads(Path({str(VIDEO1 / 'lesson.json')!r}).read_text())
setup = lesson['demo_setup']; hook = lesson['chapters'][0]['actions'][0]
fix = lesson['chapters'][3]['actions'][1]
with SheetRecorder(Path({str(VIDEO1 / 'LogicScript_Expense_Tracker.xlsx')!r}), Path({str(tmp_path)!r})) as rec:
    rec.apply({{'do': 'clear', 'ref': setup['clear']}}, sleep=lambda s: None)
    for a in setup['rows']: rec.apply(a, sleep=lambda s: None)
    out = {{}}
    rec.apply(hook, sleep=lambda s: None); out['hook'] = {{r: rec.value(r) for r in hook['expect']}}
    rec.apply(fix, sleep=lambda s: None); out['fix'] = {{r: rec.value(r) for r in fix['expect']}}
    out['summary'] = rec.value('Summary!B4')
print(json.dumps(out))
''')
    env = {**os.environ, 'PYTHONPATH': os.pathsep.join(sys.path)}
    p = subprocess.run(['xvfb-run', '-a', '-s', '-screen 0 1920x1080x24', sys.executable, str(script)],
                       capture_output=True, text=True, timeout=180, env=env)
    assert p.returncode == 0, p.stderr[-1500:]
    out = json.loads(p.stdout.strip().splitlines()[-1])
    assert out['hook'] == {'Expenses!J9': 'ERROR', 'Expenses!K9': 'Amount is not a number.'}
    assert out['fix'] == {'Expenses!J9': 'OK'}
    assert out['summary'] == 'ALL CHECKS PASSED'
    # the published template itself is never modified by recording
    assert not (VIDEO1 / '.~lock.LogicScript_Expense_Tracker.xlsx#').exists()


# ---------------- release guard ----------------

def test_draft_render_can_never_be_packaged(tmp_path):
    from channel.lesson_release import LessonReleaseError, build_candidate
    art = tmp_path / 'art'; art.mkdir()
    for name in ('final.mp4', 'thumbnail.jpg', 'captions.srt'):
        (art / name).write_bytes(b'x' * 100)
    (art / 'qc_report.json').write_text(json.dumps({'draft': True, 'method': 'estimated_draft', 'chapters': []}))
    with pytest.raises(LessonReleaseError, match='DRAFT'):
        build_candidate(art, VIDEO1, tmp_path / 'cand', topic='t', thumbnail_text='IT CAUGHT IT')
