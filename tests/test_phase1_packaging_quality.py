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
from channel.packaging_lint import QualityPolicy, lint_packaging
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

def test_real_prepared_title_gets_desktop_warning_not_rejection_by_default():
    report = lint_packaging('Boundary Testing Tutorial: The One-Cent Test (Free Browser Lab)', 'EDGE CASE')
    assert report.title_chars == 63 and report.passed
    finding = next(f for f in report.advisories if f.code == 'length')
    assert finding.source == 'project_policy' and 'not a YouTube requirement' in finding.message


@pytest.mark.parametrize('n,blocked', [(40, False), (60, False), (61, False), (100, False), (101, True)])
def test_only_youtubes_100_char_limit_blocks_by_default(n, blocked):
    report = lint_packaging('A' * n, 'Spark')
    assert (not report.passed) is blocked
    if blocked:
        assert report.blocking[0].source == 'youtube'


def test_desktop_limit_is_configurable_and_can_be_enforced():
    strict = QualityPolicy(title_desktop_chars=50, title_desktop_rule='block')
    assert not lint_packaging('A' * 51, 'Spark', strict).passed
    assert lint_packaging('A' * 50, 'Spark', strict).passed
    off = QualityPolicy(title_desktop_rule='off')
    assert 'length' not in {f.code for f in lint_packaging('A' * 80, 'Spark', off).advisories}


def test_policy_loads_from_json_and_rejects_unknown_keys(tmp_path):
    good = tmp_path / 'policy.json'; good.write_text(json.dumps({'thumbnail_max_words': 5}))
    assert QualityPolicy.load(good).thumbnail_max_words == 5
    bad = tmp_path / 'bad.json'; bad.write_text(json.dumps({'thumbnail_max_word': 5}))
    with pytest.raises(Exception):
        QualityPolicy.load(bad)
    assert QualityPolicy.load(None) == QualityPolicy()


def test_youtube_forbidden_angle_brackets_block():
    report = lint_packaging('Use <script> safely', 'Spark')
    assert report.blocking[0].code == 'forbidden-chars' and report.blocking[0].source == 'youtube'


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

def test_duplicate_words_warn_by_default_including_plurals():
    report = lint_packaging('How to Review AI Automation Workflows', 'Review Your Workflow')
    assert report.passed
    finding = next(f for f in report.advisories if f.code == 'duplicate')
    assert finding.source == 'project_policy'
    assert 'review' in finding.message and 'workflow' in finding.message
    enforced = lint_packaging('How to Review AI Automation Workflows', 'Review Your Workflow',
                              QualityPolicy(thumbnail_duplicate_rule='block'))
    assert {f.code for f in enforced.blocking} == {'duplicate'}


def test_distinct_pairing_has_no_pairing_findings_and_stopwords_ignored():
    for title, thumb in [('How to Test an Expense Rule', 'ONE CENT OFF'), ('How the Rule Breaks', 'The Missing Cent')]:
        report = lint_packaging(title, thumb)
        assert not {'duplicate', 'thumbnail-length'} & {f.code for f in report.advisories + report.blocking}


def test_thumbnail_word_count_warns_by_default_and_is_configurable():
    report = lint_packaging('Test an Expense Rule', 'one cent above the limit')
    assert report.passed and 'thumbnail-length' in {f.code for f in report.advisories}
    relaxed = lint_packaging('Test an Expense Rule', 'one cent above the limit', QualityPolicy(thumbnail_max_words=5))
    assert 'thumbnail-length' not in {f.code for f in relaxed.advisories}
    strict = lint_packaging('Test an Expense Rule', 'one cent above the limit', QualityPolicy(thumbnail_word_rule='block'))
    assert not strict.passed


def test_make_thumbnail_records_text_and_advisories_without_rejecting(tmp_path):
    image = make_thumbnail('Expense Rules', tmp_path / 'dup.jpg', title='Test Your Expense Rule')
    side = json.loads((tmp_path / 'dup.jpg.text.json').read_text())
    assert side['text'] == 'Expense Rules' and side['advisories'][0]['code'] == 'duplicate'
    with pytest.raises(ValueError, match='project policy'):
        make_thumbnail('Expense Rules', tmp_path / 'strict.jpg', title='Test Your Expense Rule',
                       policy=QualityPolicy(thumbnail_duplicate_rule='block'))
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
                                         timeline=[{'title': 'A', 'start': 0}, {'title': 'B', 'start': 5}],
                                         video_duration_s=40)
    # Only the invalid chapters block; title length and duplication are project-policy warnings.
    assert report['passed'] is False
    assert all(b.startswith('[youtube] chapters') for b in report['blocking'])
    advice = ' | '.join(report['advisory']['packaging'])
    assert '[project_policy] length' in advice and '[project_policy] duplicate' in advice
    assert 'hook' not in ' '.join(report['blocking'])  # never a blocking reason
    assert report['policy'] == QualityPolicy().model_dump()


def test_invalid_chapters_can_be_downgraded_and_are_then_omitted():
    report, chapters = evaluate_release_quality(
        make_script(), thumbnail_text='ONE CENT', timeline=[{'title': 'A', 'start': 0}],
        video_duration_s=40, policy=QualityPolicy(invalid_chapters_rule='warn'))
    assert report['passed'] and chapters is None
    assert any('omitted from the description' in a for a in report['advisory']['packaging'])


def test_missing_thumbnail_text_is_advisory_by_default():
    report, _ = evaluate_release_quality(make_script(), thumbnail_text=None)
    assert report['passed']
    assert any('thumbnail-text' in a for a in report['advisory']['packaging'])


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


def _package_args(draft, video, thumb, review, out, chapters, *extra):
    return ['package', '--draft', str(draft), '--video', str(video), '--thumbnail', str(thumb),
            '--editorial-report', str(review), '--out', str(out), '--chapters', str(chapters), *extra]


def _review(tmp_path):
    review = tmp_path / 'editorial.json'
    review.write_text(json.dumps({'gate_passed': True, 'human_reviewed': True, 'quality_passed': True}))
    return review


def _chapter_file(tmp_path, entries, name='render_report.json'):
    path = tmp_path / name
    path.write_text(json.dumps({'chapters': entries}))
    return path


def test_cli_package_duplicate_thumbnail_warns_but_packages(tmp_path, capsys):
    from channel.cli import main
    draft = tmp_path / 'draft'; _write_draft(draft, 'How to Review AI Automation Workflows')
    video = tmp_path / 'video.mp4'; _tiny_mp4(video, seconds=40)
    chapters = _chapter_file(tmp_path, [{'title': 'Start', 'start': 0}, {'title': 'Checklist', 'start': 12},
                                        {'title': 'Wrap up', 'start': 25}])
    thumb = make_thumbnail('Review Workflows', tmp_path / 'dup.jpg')
    assert main(_package_args(draft, video, thumb, _review(tmp_path), tmp_path / 'rel', chapters)) == 0
    capsys.readouterr()
    meta = json.loads((tmp_path / 'rel' / 'metadata.json').read_text())
    assert '00:12 Checklist' in meta['description']
    quality = json.loads((tmp_path / 'rel' / 'quality_report.json').read_text())
    assert quality['passed'] is True and quality['blocking'] == []
    assert any('[project_policy] duplicate' in a for a in quality['advisory']['packaging'])
    assert quality['chapters']['final_chapter_checked'] is True


def test_cli_package_policy_file_can_enforce_pairing(tmp_path, capsys):
    from channel.cli import main
    draft = tmp_path / 'draft'; _write_draft(draft, 'How to Review AI Automation Workflows')
    video = tmp_path / 'video.mp4'; _tiny_mp4(video, seconds=40)
    chapters = _chapter_file(tmp_path, [{'title': 'Start', 'start': 0}, {'title': 'Checklist', 'start': 12},
                                        {'title': 'Wrap up', 'start': 25}])
    policy = tmp_path / 'policy.json'; policy.write_text(json.dumps({'thumbnail_duplicate_rule': 'block'}))
    thumb = make_thumbnail('Review Workflows', tmp_path / 'dup.jpg')
    code = main(_package_args(draft, video, thumb, _review(tmp_path), tmp_path / 'rel', chapters,
                              '--quality-policy', str(policy)))
    out = json.loads(capsys.readouterr().out)
    assert code == 2 and out['packaged'] is False and not (tmp_path / 'rel').exists()


def test_cli_package_uses_real_video_duration_for_final_chapter(tmp_path, capsys):
    from channel.cli import main
    draft = tmp_path / 'draft'; _write_draft(draft, 'Review AI Automation Workflows')
    thumb = make_thumbnail('ONE CHECKLIST', tmp_path / 'thumb.jpg')
    # Narration timeline says the last chapter starts at 25 s and lasts 20 s, but the real
    # MP4 is only 30 s long: the real final chapter is 5 s and YouTube would ignore the list.
    timeline = [{'title': 'Start', 'start': 0, 'end': 12}, {'title': 'Checklist', 'start': 12, 'end': 25},
                {'title': 'Wrap up', 'start': 25, 'end': 45}]
    short = tmp_path / 'short.mp4'; _tiny_mp4(short, seconds=30)
    code = main(_package_args(draft, short, thumb, _review(tmp_path), tmp_path / 'rel_short',
                              _chapter_file(tmp_path, timeline)))
    out = json.loads(capsys.readouterr().out)
    # Normalisation folds the 5 s tail into "Checklist", leaving only 2 chapters: blocked, not published broken.
    assert code == 2 and any('at least 3' in b for b in out['blocking'])

    longer = tmp_path / 'long.mp4'; _tiny_mp4(longer, seconds=50)
    assert main(_package_args(draft, longer, thumb, _review(tmp_path), tmp_path / 'rel_long',
                              _chapter_file(tmp_path, timeline, 'r2.json'))) == 0
    capsys.readouterr()
    quality = json.loads((tmp_path / 'rel_long' / 'quality_report.json').read_text())
    assert quality['chapters']['passed'] and 49 <= quality['chapters']['video_duration_s'] <= 51


def test_cli_quality_check_writes_nothing(tmp_path, capsys):
    from channel.cli import main
    draft = tmp_path / 'draft'; _write_draft(draft, 'Boundary Testing Tutorial: The One-Cent Test (Free Browser Lab)')
    before = sorted(p.name for p in draft.iterdir())
    assert main(['quality-check', '--draft', str(draft), '--thumbnail-text', 'ONE CENT?']) == 0
    out = json.loads(capsys.readouterr().out)
    assert out['passed'] is True
    assert any('[project_policy] length' in a for a in out['advisory']['packaging'])
    assert sorted(p.name for p in draft.iterdir()) == before


def test_quality_report_change_after_owner_approval_invalidates_it(tmp_path):
    from channel.metadata import ReleaseMetadata
    from channel.release import check_approval
    thumb = make_thumbnail('ONE CENT OFF', tmp_path / 'thumb.jpg')
    video = tmp_path / 'video.mp4'; _tiny_mp4(video)
    manifest = build_release(tmp_path / 'rel', video, thumb,
                             ReleaseMetadata(title='T', description='D', contains_synthetic_media=False),
                             editorial_report=_review(tmp_path), quality_report={'passed': True, 'advisory': {}})
    approve_release(tmp_path / 'rel', manifest['release_digest'], human_confirmed=True)
    assert check_approval(tmp_path / 'rel')['release_digest'] == manifest['release_digest']
    (tmp_path / 'rel' / 'quality_report.json').write_text('{"passed": true, "advisory": {"edited": 1}}')
    with pytest.raises(Exception, match='quality_report.json'):
        check_approval(tmp_path / 'rel')
    (tmp_path / 'rel' / 'quality_report.json').unlink()
    with pytest.raises(Exception, match='quality_report.json'):
        check_approval(tmp_path / 'rel')


@pytest.mark.parametrize('topic,title,hook,headings', [
    ('podcast audio cleanup', 'Clean Up Podcast Audio Without Paid Plugins',
     'Your listeners leave when the first minute sounds muddy.', ['Find the noise floor', 'Gate and compress', 'Export checks']),
    ('spreadsheet date errors', 'Why Spreadsheet Dates Break Imports',
     'One wrong date format can corrupt every row you import.', ['ISO dates', 'Locale traps', 'A safe import test', 'Fixing old files']),
    ('API rate limits', 'Handle API Rate Limits Before They Handle You',
     'Most integrations fail on the second busy day, not the first.', ['Read the headers', 'Back off', 'Queue work']),
])
def test_works_for_future_videos_not_just_the_first_lesson(topic, title, hook, headings):
    script = make_script(topic=topic, title=title, hook=hook,
                         sections=[ScriptSection(heading=h, narration='x', claim_ids=['c1']) for h in headings])
    durations = [7.0] + [40.0 + 5 * i for i in range(len(headings))] + [6.0]
    timeline = timeline_from_segments('Introduction', headings, durations)
    total = sum(durations)
    report, chapters = evaluate_release_quality(script, thumbnail_text='FAST FIX', timeline=timeline,
                                                video_duration_s=total)
    assert report['passed'], report['blocking']
    assert [c.title for c in chapters] == headings
    intro = description_intro(script)
    assert intro.splitlines()[0] == hook and topic in intro
    assert derive_tags(script)[0] == topic
    assert report['advisory']['hook']['hook'] == hook


def test_description_strips_youtube_forbidden_characters():
    script, research, gate = sample_artifacts()
    script.hook = 'Is <this> safe?'
    meta = generate_metadata(script, research, gate)
    assert '<' not in meta.description and '>' not in meta.description
