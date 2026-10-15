"""Offline tests for Phase 1 packaging quality: title/thumbnail lint, chapters,
advisory hook score, dynamic descriptions and their wiring into the CLI/release."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from channel.chapters import (Chapter, format_chapters, format_timestamp, load_timeline,
                              normalize_timeline, timeline_from_segments, validate_chapters)
from channel.metadata import derive_tags, description_intro, generate_metadata
from channel.packaging_lint import lint_packaging
from channel.quality import evaluate_release_quality
from channel.release import build_release, approve_release
from channel.thumbnail import make_thumbnail, read_thumbnail_text
from pipeline.hook_score import load_formulas, score_hook
from pipeline.models import ScriptArtifact, ScriptSection
from tests.test_channel_release import sample_artifacts


def make_script(**overrides) -> ScriptArtifact:
    data = dict(topic='invoice approval rules', title='Test Your Invoice Approval Rule',
                hook='You can approve the wrong invoice even when every obvious test passes.',
                sections=[ScriptSection(heading='Why boundaries fail', narration='x', claim_ids=['c1']),
                          ScriptSection(heading='Build a test matrix', narration='x', claim_ids=['c1']),
                          ScriptSection(heading='Run the checks', narration='x', claim_ids=['c1'])],
                cta='Try it on your own rule.', duration_s=300, word_count=800,
                verified_at='2026-10-01T00:00:00+00:00')
    data.update(overrides)
    return ScriptArtifact(**data)


# ---------- 1. title length / truncation ----------

def test_real_prepared_title_is_blocked_for_desktop_truncation():
    report = lint_packaging('Boundary Testing Tutorial: The One-Cent Test (Free Browser Lab)', 'EDGE CASE')
    assert report.title_chars == 63
    assert [f.code for f in report.blocking] == ['length']
    assert not report.passed


@pytest.mark.parametrize('n,blocked', [(40, False), (60, False), (61, True), (101, True)])
def test_title_length_boundaries(n, blocked):
    report = lint_packaging('A' * n, 'Spark')
    assert (not report.passed) is blocked


def test_mobile_preview_is_advisory_not_blocking():
    report = lint_packaging('Before You Automate: Test the One-Cent Boundary', 'ONE CENT?')
    assert report.mobile_preview == 'Before You Automate: Test the One-Cent...'
    assert 'mobile' in [f.code for f in report.advisories]
    assert 'mobile' not in [f.code for f in report.blocking]


def test_style_issues_never_block():
    report = lint_packaging('THE BEST AMAZING HUGE Trick', 'Fresh angle')
    assert report.passed
    assert {'shouting', 'vague', 'no-anchor'} <= {f.code for f in report.advisories}


# ---------- 2. title / thumbnail duplication ----------

def test_duplicate_words_block_including_plurals():
    report = lint_packaging('How to Review AI Automation Workflows', 'Review Your Workflow')
    codes = {f.code for f in report.blocking}
    assert 'duplicate' in codes
    msg = next(f.message for f in report.blocking if f.code == 'duplicate')
    assert 'review' in msg and 'workflow' in msg


def test_distinct_pairing_passes_and_stopwords_ignored():
    assert lint_packaging('How to Test an Expense Rule', 'ONE CENT OFF').passed
    assert lint_packaging('How the Rule Breaks', 'The Missing Cent').passed  # 'the' is a stopword


def test_thumbnail_word_ceiling():
    report = lint_packaging('Test an Expense Rule', 'one cent above the limit')
    assert 'thumbnail-length' in {f.code for f in report.blocking}


def test_make_thumbnail_checks_pairing_and_records_text(tmp_path):
    with pytest.raises(ValueError, match='repeats the title'):
        make_thumbnail('Expense Rules', tmp_path / 'bad.jpg', title='Test Your Expense Rule')
    image = make_thumbnail('ONE CENT OFF', tmp_path / 'good.jpg', title='Test Your Expense Rule')
    assert read_thumbnail_text(image) == 'ONE CENT OFF'
    # Existing callers without a title keep working unchanged.
    assert make_thumbnail('Review Your Workflow', tmp_path / 'legacy.jpg').is_file()


# ---------- 3. chapters ----------

def test_chapter_rules():
    ok = [Chapter(start_s=0, title='Intro'), Chapter(start_s=30, title='Setup'), Chapter(start_s=95, title='Run')]
    assert validate_chapters(ok, video_duration_s=200).passed
    bad_start = [Chapter(start_s=5, title='A'), Chapter(start_s=30, title='B'), Chapter(start_s=60, title='C')]
    assert 'first chapter must start at 00:00' in validate_chapters(bad_start).errors
    too_few = ok[:2]
    assert any('at least 3' in e for e in validate_chapters(too_few).errors)
    short = [Chapter(start_s=0, title='A'), Chapter(start_s=8, title='B'), Chapter(start_s=60, title='C')]
    assert any('minimum is 10s' in e for e in validate_chapters(short).errors)
    short_tail = validate_chapters(ok, video_duration_s=100)
    assert any('last chapter' in e for e in short_tail.errors)
    empty_title = [Chapter(start_s=0, title=' '), Chapter(start_s=30, title='B'), Chapter(start_s=60, title='C')]
    assert any('empty title' in e for e in validate_chapters(empty_title).errors)


def test_normalize_merges_short_hook_and_cta():
    timeline = timeline_from_segments('Introduction', ['Why it fails', 'Build the matrix', 'Run it'],
                                      [6.5, 80.0, 95.0, 70.0, 4.0])
    chapters = normalize_timeline(timeline)
    # 6.5 s hook merges into the first section, which keeps 00:00; CTA folds into the last section.
    assert [c.title for c in chapters] == ['Why it fails', 'Build the matrix', 'Run it']
    assert chapters[0].start_s == 0
    assert validate_chapters(chapters, video_duration_s=255.5).passed
    assert format_chapters(chapters).splitlines()[0] == '00:00 Why it fails'


def test_timestamps_and_hours():
    assert format_timestamp(0) == '00:00'
    assert format_timestamp(407.04) == '06:47'
    assert format_timestamp(3725) == '1:02:05'


def test_load_timeline_from_render_report(tmp_path):
    report = tmp_path / 'qc_report.json'
    report.write_text(json.dumps({'chapters': [{'title': 'A', 'start': 0, 'end': 20}]}))
    assert load_timeline(report)[0]['title'] == 'A'
    (tmp_path / 'bad.json').write_text('{"x":1}')
    with pytest.raises(ValueError):
        load_timeline(tmp_path / 'bad.json')


def test_real_lesson_timeline_produces_valid_chapters():
    lesson = json.loads(Path('content/expense-rule-lesson/lesson.json').read_text())
    # Synthetic equal timing over the real 18 lesson chapter titles (no render needed).
    timeline = [{'title': c['title'], 'start': i * 22.6, 'end': (i + 1) * 22.6}
                for i, c in enumerate(lesson['chapters'])]
    chapters = normalize_timeline(timeline)
    assert len(chapters) == len(lesson['chapters'])
    assert validate_chapters(chapters, video_duration_s=18 * 22.6).passed


# ---------- 4. advisory hook score ----------

def test_hook_score_matches_upstream_reference_values():
    # Values produced by the unmodified upstream hookscore.py on these exact hooks.
    real = score_hook('A rule can pass the obvious tests and still approve the wrong request. '
                      'Watch what happens when we move a travel expense just one cent above its limit.')
    assert real.properties == {'specificity': 35, 'address': 26, 'stakes': 22, 'curiosity': 41, 'brevity': 72}
    assert real.verdict == 32 and real.band == 'WEAK'
    junk = score_hook('Welcome back to the channel, today we are going to talk about some amazing automation tips.')
    assert junk.verdict == 22
    assert real.advisory is True and junk.advisory is True


def test_hook_formulas_loaded_with_attribution():
    data = json.loads(Path('pipeline/hook_formulas.json').read_text())
    assert data['attribution']['license'] == 'MIT'
    assert len(load_formulas()) == 21


def test_specificity_advice_does_not_ask_for_numbers():
    result = score_hook('Welcome to the channel, this is amazing stuff')
    assert result.weakest == 'specificity'
    assert 'cited claim' in result.suggestion


def test_weak_hook_never_blocks_quality_report():
    script = make_script(hook='Hi.')
    report, _ = evaluate_release_quality(script, thumbnail_text='ONE CENT OFF')
    assert report['advisory']['hook']['band'] == 'WEAK'
    assert report['passed'] is True and report['blocking'] == []


# ---------- 5. dynamic descriptions ----------

def test_description_is_topic_specific_and_not_hardcoded():
    script = make_script()
    intro = description_intro(script)
    assert intro.splitlines()[0] == 'You can approve the wrong invoice even when every obvious test passes.'
    assert 'invoice approval rules' in intro.splitlines()[1]
    assert 'why boundaries fail' in intro
    other = make_script(topic='podcast audio cleanup', hook='Your podcast loses listeners in the first minute.')
    assert description_intro(other) != intro
    for s in (script, other):
        assert 'small businesses can evaluate AI automation' not in description_intro(s)


def test_generate_metadata_adds_valid_chapters_and_rejects_invalid():
    script, research, gate = sample_artifacts()
    chapters = [Chapter(start_s=0, title='Start'), Chapter(start_s=20, title='Checklist'),
                Chapter(start_s=45, title='Next step')]
    meta = generate_metadata(script, research, gate, chapters=chapters, video_duration_s=70)
    assert 'Chapters:\n00:00 Start\n00:20 Checklist\n00:45 Next step' in meta.description
    assert meta.description.index('Chapters:') < meta.description.index('Sources referenced')
    with pytest.raises(ValueError, match='Chapters invalid'):
        generate_metadata(script, research, gate, chapters=chapters[:2])
    assert 'https://example.com/research' in meta.description


def test_tags_derive_from_this_video_only():
    tags = derive_tags(make_script())
    assert tags[0] == 'invoice approval rules'
    assert 'small business automation' not in tags and 'AI automation' not in tags
    assert len(tags) <= 15 and sum(len(t) for t in tags) < 500


# ---------- wiring: quality report, release package, CLI ----------

def test_quality_report_separates_blocking_from_advisory():
    script = make_script(title='Boundary Testing Tutorial: The One-Cent Test (Free Browser Lab)')
    report, _ = evaluate_release_quality(script, thumbnail_text='Boundary Testing',
                                         timeline=[{'title': 'A', 'start': 0}, {'title': 'B', 'start': 5}])
    assert report['passed'] is False
    joined = ' | '.join(report['blocking'])
    assert 'length' in joined and 'duplicate' in joined and 'chapters' in joined
    assert 'hook' not in joined  # the hook score is never a blocking reason
    assert 'hook' in report['advisory']


def test_missing_thumbnail_text_blocks():
    report, _ = evaluate_release_quality(make_script(), thumbnail_text=None)
    assert any(b.startswith('thumbnail-text') for b in report['blocking'])


def _tiny_mp4(path: Path, seconds: int = 1):
    subprocess.run(['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error',
                    '-f', 'lavfi', '-i', f'color=c=blue:s=320x180:d={seconds}:r=10',
                    '-f', 'lavfi', '-i', f'sine=frequency=220:duration={seconds}',
                    '-c:v', 'libx264', '-preset', 'ultrafast', '-c:a', 'aac', '-shortest', str(path)],
                   capture_output=True, check=True)


def test_quality_report_is_hashed_into_release(tmp_path):
    from channel.metadata import ReleaseMetadata
    thumb = make_thumbnail('ONE CENT OFF', tmp_path / 'thumb.jpg')
    video = tmp_path / 'video.mp4'; _tiny_mp4(video)
    review = tmp_path / 'editorial.json'
    review.write_text(json.dumps({'gate_passed': True, 'human_reviewed': True, 'quality_passed': True}))
    manifest = build_release(tmp_path / 'rel', video, thumb,
                             ReleaseMetadata(title='T', description='D', contains_synthetic_media=False),
                             editorial_report=review, quality_report={'passed': True, 'advisory': {}})
    assert 'quality_report.json' in manifest['hashes']
    (tmp_path / 'rel' / 'quality_report.json').write_text('{"passed": false}')
    with pytest.raises(Exception, match='changed'):
        approve_release(tmp_path / 'rel', manifest['release_digest'], human_confirmed=True)


def _write_draft(folder: Path, title: str):
    script, research, gate = sample_artifacts()
    script.title = title
    folder.mkdir()
    (folder / 'script.json').write_text(script.model_dump_json())
    (folder / 'research.json').write_text(research.model_dump_json())
    (folder / 'verification_gate.json').write_text(gate.model_dump_json())


def test_cli_package_blocks_bad_pairing_and_packages_good_one(tmp_path, capsys):
    from channel.cli import main
    draft = tmp_path / 'draft'; _write_draft(draft, 'How to Review AI Automation Workflows')
    video = tmp_path / 'video.mp4'; _tiny_mp4(video, seconds=40)
    review = tmp_path / 'editorial.json'
    review.write_text(json.dumps({'gate_passed': True, 'human_reviewed': True, 'quality_passed': True}))
    chapters = tmp_path / 'render_report.json'
    chapters.write_text(json.dumps({'chapters': [{'title': 'Start', 'start': 0}, {'title': 'Checklist', 'start': 12},
                                                 {'title': 'Wrap up', 'start': 25}]}))

    bad_thumb = make_thumbnail('Review Workflows', tmp_path / 'bad.jpg')
    code = main(['package', '--draft', str(draft), '--video', str(video), '--thumbnail', str(bad_thumb),
                 '--editorial-report', str(review), '--out', str(tmp_path / 'rel_bad'), '--chapters', str(chapters)])
    out = json.loads(capsys.readouterr().out)
    assert code == 2 and out['packaged'] is False and not (tmp_path / 'rel_bad').exists()

    good_thumb = make_thumbnail('ONE CHECKLIST', tmp_path / 'good.jpg')
    code = main(['package', '--draft', str(draft), '--video', str(video), '--thumbnail', str(good_thumb),
                 '--editorial-report', str(review), '--out', str(tmp_path / 'rel'), '--chapters', str(chapters)])
    capsys.readouterr()
    assert code == 0
    meta = json.loads((tmp_path / 'rel' / 'metadata.json').read_text())
    assert '00:12 Checklist' in meta['description']
    quality = json.loads((tmp_path / 'rel' / 'quality_report.json').read_text())
    assert quality['passed'] is True and 'hook' in quality['advisory']


def test_cli_quality_check_writes_nothing(tmp_path, capsys):
    from channel.cli import main
    draft = tmp_path / 'draft'; _write_draft(draft, 'Boundary Testing Tutorial: The One-Cent Test (Free Browser Lab)')
    before = sorted(p.name for p in draft.iterdir())
    assert main(['quality-check', '--draft', str(draft), '--thumbnail-text', 'ONE CENT?']) == 0
    out = json.loads(capsys.readouterr().out)
    assert out['passed'] is False and out['blocking'][0].startswith('length')
    assert sorted(p.name for p in draft.iterdir()) == before
