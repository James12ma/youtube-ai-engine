"""Offline tests: hardened uploader, lesson release builder and the upload workflow."""
from __future__ import annotations

import json
import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest
import yaml

from channel.lesson_release import (LessonReleaseError, build_candidate, finalize_release, safe_extract,
                                    source_urls, zip_folder)
from channel.release import approve_release, check_approval
from channel.youtube import UploadBlocked, upload_youtube

LESSON = Path('content/expense-rule-lesson')
THUMB_TEXT = 'THE ONE-CENT BOUNDARY TEST $100.00 $100.01'


def _mp4(path: Path, seconds: int):
    subprocess.run(['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error',
                    '-f', 'lavfi', '-i', f'color=c=navy:s=320x180:d={seconds}:r=5',
                    '-f', 'lavfi', '-i', f'sine=frequency=330:duration={seconds}',
                    '-c:v', 'libx264', '-preset', 'ultrafast', '-c:a', 'aac', '-shortest', str(path)],
                   capture_output=True, check=True)


@pytest.fixture(scope='module')
def fake_artifact(tmp_path_factory):
    """Stand-in for the lesson-polished artifact: same file names, real 18-chapter timeline."""
    art = tmp_path_factory.mktemp('artifact')
    lesson = json.loads((LESSON / 'lesson.json').read_text())
    step = 22.0
    duration = int(step * len(lesson['chapters'])) + 2
    _mp4(art / 'final.mp4', duration)
    from PIL import Image
    Image.new('RGB', (1280, 720), '#0b1021').save(art / 'thumbnail.jpg', quality=90)
    (art / 'captions.srt').write_text('1\n00:00:00,000 --> 00:00:02,000\nA rule can pass.\n')
    timeline = [{'title': c['title'], 'start': i * step, 'end': (i + 1) * step}
                for i, c in enumerate(lesson['chapters'])]
    (art / 'qc_report.json').write_text(json.dumps({'chapters': timeline, 'narration_backend': 'piper'}))
    (art / 'independent_gates.json').write_text(json.dumps({'passed': True}))
    (art / 'LogicScript_Practice_Lab.html').write_text('<!doctype html><title>lab</title>')
    return art


def _candidate(tmp_path, art, **kw):
    return build_candidate(art, LESSON, tmp_path / 'candidate',
                           topic='boundary testing for an expense approval rule',
                           thumbnail_text=THUMB_TEXT, **kw)


# ---------------- lesson candidate ----------------

def test_candidate_contains_everything_for_review(tmp_path, fake_artifact):
    result = _candidate(tmp_path, fake_artifact)
    cand = tmp_path / 'candidate'
    for name in ('video.mp4', 'thumbnail.jpg', 'captions.srt', 'metadata.json', 'description.txt',
                 'tags.txt', 'chapters.txt', 'quality_report.json', 'CANDIDATE_STATUS.json',
                 'LogicScript_Practice_Lab.html'):
        assert (cand / name).is_file(), name
    assert result['stage'] == 'CANDIDATE - NOT APPROVED'
    assert result['chapters'] == 18 and result['quality_passed'] is True
    meta = json.loads((cand / 'metadata.json').read_text())
    assert meta['title'] == 'Before You Automate: Test the One-Cent Boundary'
    assert meta['contains_synthetic_media'] is None  # owner must decide
    assert not (cand / 'manifest.json').exists() and not (cand / 'OWNER_APPROVAL.json').exists()


def test_candidate_description_is_specific_attributed_and_sourced(tmp_path, fake_artifact):
    _candidate(tmp_path, fake_artifact)
    desc = (tmp_path / 'candidate' / 'description.txt').read_text()
    assert desc.splitlines()[0] == 'A rule can pass the obvious tests and still approve the wrong request.'
    assert 'Chapters:\n00:00 The one-cent test' in desc
    assert 'CC BY 4.0' in desc and 'https://www.openslr.org/60/' in desc  # LibriTTS licence attribution
    for url in ('https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html',
                'https://docs.python.org/3/library/decimal.html'):
        assert url in desc
    assert 'invented teaching examples' in desc
    assert 'practice lab (runs' not in desc  # no URL invented
    assert '<' not in desc and '>' not in desc and len(desc.encode()) <= 5000


def test_candidate_records_policy_advisories_not_blocks(tmp_path, fake_artifact):
    _candidate(tmp_path, fake_artifact)
    report = json.loads((tmp_path / 'candidate' / 'quality_report.json').read_text())
    advice = ' | '.join(report['advisory']['packaging'])
    assert '[project_policy] duplicate' in advice      # thumbnail repeats one/cent/boundary/test
    assert '[project_policy] thumbnail-length' in advice
    assert 'practice-lab' in advice
    assert report['chapters']['final_chapter_checked'] is True
    assert report['advisory']['hook']['advisory'] is True


def test_candidate_practice_url_validated_and_included(tmp_path, fake_artifact):
    with pytest.raises(LessonReleaseError, match='https'):
        _candidate(tmp_path, fake_artifact, practice_url='javascript:alert(1)')
    _candidate(tmp_path, fake_artifact, practice_url='https://example.org/lab.html')
    assert 'https://example.org/lab.html' in (tmp_path / 'candidate' / 'description.txt').read_text()


def test_candidate_blocks_when_real_video_is_too_short_for_chapters(tmp_path, fake_artifact):
    art = tmp_path / 'short_art'
    shutil.copytree(fake_artifact, art)
    _mp4(art / 'final.mp4', 30)  # chapters claim ~396 s
    result = build_candidate(art, LESSON, tmp_path / 'c', topic='t', thumbnail_text='EDGE CASE')
    assert result['quality_passed'] is False and result['blocking']


def test_source_urls_exclude_licence_links():
    urls = source_urls((LESSON / 'sources.md').read_text())
    assert urls and not any('openslr' in u or 'creativecommons' in u for u in urls)


# ---------------- finalize ----------------

def test_finalize_requires_matching_video_hash_and_statement(tmp_path, fake_artifact):
    result = _candidate(tmp_path, fake_artifact)
    with pytest.raises(LessonReleaseError, match='hash'):
        finalize_release(tmp_path / 'candidate', tmp_path / 'rel', owner_approval_statement='Approved after full review',
                         contains_synthetic_media=False, video_sha256='0' * 64)
    with pytest.raises(LessonReleaseError, match='statement'):
        finalize_release(tmp_path / 'candidate', tmp_path / 'rel', owner_approval_statement='ok',
                         contains_synthetic_media=False, video_sha256=result['video_sha256'])
    manifest = finalize_release(tmp_path / 'candidate', tmp_path / 'rel',
                                owner_approval_statement='Approved after full review on phone',
                                contains_synthetic_media=False, video_sha256=result['video_sha256'])
    assert set(manifest['hashes']) >= {'video.mp4', 'thumbnail.jpg', 'captions.srt', 'metadata.json',
                                       'quality_report.json', 'editorial_review.json'}
    meta = json.loads((tmp_path / 'rel' / 'metadata.json').read_text())
    assert meta['contains_synthetic_media'] is False
    review = json.loads((tmp_path / 'rel' / 'editorial_review.json').read_text())
    assert 'not the automated VerificationGate' in review['gate_basis']


def test_release_zip_roundtrip_and_digest_survive(tmp_path, fake_artifact):
    result = _candidate(tmp_path, fake_artifact)
    manifest = finalize_release(tmp_path / 'candidate', tmp_path / 'rel',
                                owner_approval_statement='Approved after full review on phone',
                                contains_synthetic_media=True, video_sha256=result['video_sha256'])
    z = zip_folder(tmp_path / 'rel', tmp_path / 'release.zip')
    out = safe_extract(z, tmp_path / 'extracted')
    approve_release(out, manifest['release_digest'], human_confirmed=True)
    assert check_approval(out)['release_digest'] == manifest['release_digest']


@pytest.mark.parametrize('name', ['../evil.txt', 'sub/dir.txt', '.hidden', '/abs.txt'])
def test_safe_extract_rejects_unsafe_entries(tmp_path, name):
    z = tmp_path / 'bad.zip'
    with zipfile.ZipFile(z, 'w') as archive:
        archive.writestr(name, 'x')
    with pytest.raises(LessonReleaseError):
        safe_extract(z, tmp_path / 'out')


# ---------------- uploader ----------------

def _approved_release(tmp_path, fake_artifact):
    result = _candidate(tmp_path, fake_artifact)
    manifest = finalize_release(tmp_path / 'candidate', tmp_path / 'rel',
                                owner_approval_statement='Approved after full review on phone',
                                contains_synthetic_media=False, video_sha256=result['video_sha256'])
    approve_release(tmp_path / 'rel', manifest['release_digest'], human_confirmed=True)
    return tmp_path / 'rel', manifest


class HttpError(Exception):
    def __init__(self, status):
        super().__init__('boom with body that must not be logged')
        self.resp = type('R', (), {'status': status})()


def _fake_api(log, *, fail_chunks=(), thumb_error=None):
    chunks = list(fail_chunks)

    class Request:
        def next_chunk(self):
            if chunks:
                raise chunks.pop(0)
            return None, {'id': 'VID123'}

    class Exec:
        def __init__(self, name, kwargs): self.name, self.kwargs = name, kwargs
        def execute(self):
            log.append((self.name, self.kwargs))
            if self.name == 'thumbnail' and thumb_error:
                raise thumb_error
            return {}

    class Api:
        def videos(self):
            return type('V', (), {'insert': lambda s, **k: (log.append(('insert', k)), Request())[1]})()
        def thumbnails(self):
            return type('T', (), {'set': lambda s, **k: Exec('thumbnail', k)})()
        def captions(self):
            return type('C', (), {'insert': lambda s, **k: Exec('captions', k)})()

    return lambda: (Api(), lambda path: ('video', str(path)), lambda path, mime: (str(path), mime))


@pytest.fixture
def upload_env(monkeypatch):
    def set_digest(d):
        monkeypatch.setenv('YOUTUBE_UPLOAD_ALLOWED', '1')
        monkeypatch.setenv('OWNER_APPROVED_RELEASE_DIGEST', d)
        monkeypatch.setenv('YOUTUBE_CLIENT_ID', 'x'); monkeypatch.setenv('YOUTUBE_CLIENT_SECRET', 'x')
        monkeypatch.setenv('YOUTUBE_REFRESH_TOKEN', 'x'); monkeypatch.delenv('YOUTUBE_TOKEN_FILE', raising=False)
        monkeypatch.delenv('YOUTUBE_PUBLIC_ALLOWED', raising=False)
    return set_digest


def test_upload_sets_thumbnail_and_writes_receipt(tmp_path, fake_artifact, upload_env):
    rel, manifest = _approved_release(tmp_path, fake_artifact)
    upload_env(manifest['release_digest'])
    log = []
    receipt = upload_youtube(rel, api_factory=_fake_api(log), sleep=lambda s: None)
    assert receipt['youtube_video_id'] == 'VID123' and receipt['thumbnail'] == 'set'
    assert receipt['captions'].startswith('skipped')
    insert = log[0][1]['body']
    assert insert['status']['privacyStatus'] == 'private'
    assert insert['status']['containsSyntheticMedia'] is False
    assert insert['snippet']['title'] == 'Before You Automate: Test the One-Cent Boundary'
    assert json.loads((rel / 'youtube_receipt.json').read_text())['thumbnail'] == 'set'


def test_upload_retries_transient_errors_only(tmp_path, fake_artifact, upload_env):
    rel, manifest = _approved_release(tmp_path, fake_artifact)
    upload_env(manifest['release_digest'])
    sleeps = []
    receipt = upload_youtube(rel, api_factory=_fake_api([], fail_chunks=[HttpError(503), HttpError(500)]),
                             sleep=sleeps.append)
    assert receipt['youtube_video_id'] == 'VID123' and len(sleeps) == 2


def test_upload_fails_closed_on_client_error_without_receipt(tmp_path, fake_artifact, upload_env):
    rel, manifest = _approved_release(tmp_path, fake_artifact)
    upload_env(manifest['release_digest'])
    with pytest.raises(UploadBlocked, match='HTTP 403') as info:
        upload_youtube(rel, api_factory=_fake_api([], fail_chunks=[HttpError(403)]), sleep=lambda s: None)
    assert 'body that must not be logged' not in str(info.value)
    assert not (rel / 'youtube_receipt.json').exists()


def test_upload_gives_up_after_bounded_retries(tmp_path, fake_artifact, upload_env):
    rel, manifest = _approved_release(tmp_path, fake_artifact)
    upload_env(manifest['release_digest'])
    with pytest.raises(UploadBlocked):
        upload_youtube(rel, api_factory=_fake_api([], fail_chunks=[HttpError(503)] * 10), sleep=lambda s: None)


def test_thumbnail_failure_keeps_receipt_and_blocks_reupload(tmp_path, fake_artifact, upload_env):
    rel, manifest = _approved_release(tmp_path, fake_artifact)
    upload_env(manifest['release_digest'])
    receipt = upload_youtube(rel, api_factory=_fake_api([], thumb_error=HttpError(403)), sleep=lambda s: None)
    assert receipt['thumbnail'].startswith('failed: HTTP 403')
    with pytest.raises(UploadBlocked, match='Receipt already exists'):
        upload_youtube(rel, api_factory=_fake_api([]), sleep=lambda s: None)


def test_upload_refuses_wrong_digest_and_public_without_gate(tmp_path, fake_artifact, upload_env):
    rel, manifest = _approved_release(tmp_path, fake_artifact)
    upload_env('f' * 64)
    with pytest.raises(UploadBlocked, match='digest'):
        upload_youtube(rel, api_factory=_fake_api([]))
    upload_env(manifest['release_digest'])
    with pytest.raises(UploadBlocked, match='Public/unlisted'):
        upload_youtube(rel, privacy='public', api_factory=_fake_api([]))


def test_captions_only_uploaded_when_explicitly_enabled(tmp_path, fake_artifact, upload_env):
    rel, manifest = _approved_release(tmp_path, fake_artifact)
    upload_env(manifest['release_digest'])
    log = []
    receipt = upload_youtube(rel, api_factory=_fake_api(log), upload_captions=True, sleep=lambda s: None)
    assert receipt['captions'] == 'uploaded' and any(name == 'captions' for name, _ in log)


# ---------------- workflow ----------------

WORKFLOW = Path('.github/workflows/youtube-upload.yml')


def _workflow():
    return yaml.safe_load(WORKFLOW.read_text())


def test_workflow_is_manual_only_and_gated():
    wf = _workflow()
    triggers = wf.get('on') or wf.get(True)
    assert set(triggers) == {'workflow_dispatch'}
    job = wf['jobs']['upload']
    for gate in ("vars.ZERO_COST_ACTIONS_CONFIRMED == '1'", "vars.YOUTUBE_UPLOAD_ALLOWED == '1'",
                 'inputs.i_watched_and_approve'):
        assert gate in job['if']
    privacy = triggers['workflow_dispatch']['inputs']['privacy']
    assert privacy['default'] == 'private' and 'public' not in privacy['options']
    assert wf['permissions'] == {'contents': 'write'}


def test_workflow_never_interpolates_inputs_or_secrets_into_shell():
    for step in _workflow()['jobs']['upload']['steps']:
        run = step.get('run', '')
        assert '${{' not in run, step.get('name')
        assert 'set -x' not in run and 'printenv' not in run
    text = WORKFLOW.read_text()
    assert 'echo $YOUTUBE' not in text and 'echo "$YOUTUBE' not in text


def test_workflow_checks_channel_before_upload_and_disables_credential_persistence():
    steps = _workflow()['jobs']['upload']['steps']
    names = [s.get('name', s.get('uses', '')) for s in steps]
    assert names.index('Confirm OAuth and the expected channel (read-only)') < \
        names.index('Upload video (private/unlisted), then thumbnail')
    assert names.index('Refuse duplicate uploads') < names.index('Upload video (private/unlisted), then thumbnail')
    assert steps[0]['with']['persist-credentials'] is False


def test_workflow_shell_blocks_parse():
    for step in _workflow()['jobs']['upload']['steps']:
        if 'run' in step:
            subprocess.run(['bash', '-n'], input=step['run'], text=True, check=True)
