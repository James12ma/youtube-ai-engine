"""Release packaging for hand-authored lessons (content/<lesson>/lesson.json).

Pipeline drafts use ``generate_metadata`` (which requires the automated verification
gate). Hand-authored lessons, such as the first LogicScript tutorial, are source-checked
manually in ``sources.md`` instead, so they get their own builder. It reuses the same
Phase 1 checks: title/thumbnail policy, YouTube chapter rules against the real MP4
duration, the advisory hook score and the YouTube-safe description helpers.

Two stages, never merged:

* ``build_candidate`` - everything the owner needs to review. No approval, no manifest.
* ``finalize_release`` - only after the owner's explicit approval of the exact video;
  produces the hashed release folder (``channel.release.build_release``) whose digest the
  owner must supply again to upload.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from pipeline.models import ScriptArtifact, ScriptSection

from .chapters import format_chapters, load_timeline
from .metadata import ReleaseMetadata, _youtube_safe, derive_tags, description_intro
from .packaging_lint import QualityPolicy
from .quality import evaluate_release_quality, probe_duration
from .release import build_release

LIBRITTS_ATTRIBUTION = (
    'Narration is a synthetic voice generated with Piper using a model trained on LibriTTS '
    '(OpenSLR 60, https://www.openslr.org/60/), licensed CC BY 4.0 '
    '(https://creativecommons.org/licenses/by/4.0/).')
ATTRIBUTION_HOSTS = ('openslr.org', 'creativecommons.org')
REQUIRED_ARTIFACT_FILES = ('final.mp4', 'thumbnail.jpg', 'captions.srt', 'qc_report.json')


class LessonReleaseError(RuntimeError):
    pass


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def lesson_as_script(lesson: dict, topic: str) -> ScriptArtifact:
    chapters = lesson['chapters']
    # The spoken hook is the opening two sentences, the span the advisory score was calibrated on.
    first = ' '.join(re.findall(r'[^.!?]+[.!?]', chapters[0]['narration'])[:2]).strip() or chapters[0]['narration']
    return ScriptArtifact(
        topic=topic, title=lesson['title'], hook=first,
        sections=[ScriptSection(heading=c['title'], narration=c['narration']) for c in chapters],
        cta=chapters[-1]['narration'], duration_s=0, word_count=sum(len(c['narration'].split()) for c in chapters),
        verified_at=datetime.now(timezone.utc).isoformat())


def source_urls(sources_md: str) -> list[str]:
    urls = re.findall(r'https://[^\s)>\]]+', sources_md)
    out = []
    for url in urls:
        url = url.rstrip('.,;')
        if any(host in url for host in ATTRIBUTION_HOSTS) or url in out:
            continue
        out.append(url)
    return out


def lesson_description(script: ScriptArtifact, chapters_block: str | None, sources: list[str], *,
                       practice_url: str | None) -> str:
    parts = [description_intro(script)]
    if practice_url:
        parts.append('Free practice lab (runs in a desktop browser, no account): ' + practice_url)
    if chapters_block:
        parts.append('Chapters:\n' + chapters_block)
    if sources:
        parts.append('Sources referenced:\n' + '\n'.join('- ' + u for u in sources))
    parts.append(LIBRITTS_ATTRIBUTION)
    parts.append('All amounts and limits shown are invented teaching examples. Educational content; '
                 'not legal, accounting or security advice.')
    desc = _youtube_safe('\n\n'.join(parts))
    if len(desc.encode('utf-8')) > 5000:
        raise LessonReleaseError('Description exceeds YouTube 5000-byte limit')
    return desc


def build_candidate(artifact_dir: Path, lesson_dir: Path, out_dir: Path, *, title: str | None = None,
                    topic: str, thumbnail_text: str, practice_url: str | None = None,
                    policy: QualityPolicy | None = None) -> dict:
    artifact_dir, lesson_dir, out_dir = Path(artifact_dir), Path(lesson_dir), Path(out_dir)
    missing = [f for f in REQUIRED_ARTIFACT_FILES if not (artifact_dir / f).is_file()]
    if missing:
        raise LessonReleaseError('Artifact folder is missing: ' + ', '.join(missing))
    if out_dir.exists() and any(out_dir.iterdir()):
        raise LessonReleaseError('Candidate folder must be new or empty')
    if practice_url is not None and not re.fullmatch(r'https://[^\s<>]+', practice_url):
        raise LessonReleaseError('Practice URL must be a plain https URL')

    lesson = json.loads((lesson_dir / 'lesson.json').read_text(encoding='utf-8'))
    script = lesson_as_script(lesson, topic)
    video = artifact_dir / 'final.mp4'
    duration = probe_duration(video)
    if duration is None:
        raise LessonReleaseError('Could not read the real MP4 duration with ffprobe')
    timeline = load_timeline(artifact_dir / 'qc_report.json')
    report, chapters = evaluate_release_quality(script, title=title, thumbnail_text=thumbnail_text,
                                                timeline=timeline, video_duration_s=duration, policy=policy)
    if not practice_url:
        report['advisory']['packaging'].append(
            '[project_policy] practice-lab: no public URL supplied; the description omits the link '
            '(the video tells viewers a free practice lab exists)')
    sources = source_urls((lesson_dir / 'sources.md').read_text(encoding='utf-8'))
    description = lesson_description(script, format_chapters(chapters) if chapters else None, sources,
                                     practice_url=practice_url)
    meta = ReleaseMetadata(title=_youtube_safe(report['title']), description=description,
                           tags=derive_tags(script), contains_synthetic_media=None)

    out_dir.mkdir(parents=True, exist_ok=True)
    copies = {'video.mp4': video, 'thumbnail.jpg': artifact_dir / 'thumbnail.jpg',
              'captions.srt': artifact_dir / 'captions.srt'}
    lab = artifact_dir / 'LogicScript_Practice_Lab.html'
    if lab.is_file():
        copies['LogicScript_Practice_Lab.html'] = lab
    for name, src in copies.items():
        shutil.copy2(src, out_dir / name)
    (out_dir / 'metadata.json').write_text(meta.model_dump_json(indent=2), encoding='utf-8')
    (out_dir / 'description.txt').write_text(meta.description + '\n', encoding='utf-8')
    (out_dir / 'tags.txt').write_text(', '.join(meta.tags) + '\n', encoding='utf-8')
    (out_dir / 'chapters.txt').write_text((format_chapters(chapters) if chapters else '') + '\n', encoding='utf-8')
    report['video_duration_s'] = duration
    report['source_artifact_sha256'] = {name: _sha(src) for name, src in copies.items()}
    for extra in ('independent_gates.json', 'qc_report.json'):
        if (artifact_dir / extra).is_file():
            report.setdefault('render_evidence', {})[extra] = json.loads((artifact_dir / extra).read_text())
    (out_dir / 'quality_report.json').write_text(json.dumps(report, indent=2, default=str), encoding='utf-8')
    status = {
        'stage': 'CANDIDATE - NOT APPROVED',
        'owner_decisions_required': [
            'watch/listen to the complete video and approve or request changes',
            'confirm the title',
            'decide YouTube altered/synthetic content disclosure (yes/no)',
            'optional: public URL for the practice lab',
        ],
        'quality_passed': report['passed'],
        'blocking': report['blocking'],
    }
    (out_dir / 'CANDIDATE_STATUS.json').write_text(json.dumps(status, indent=2), encoding='utf-8')
    return {'candidate': str(out_dir), **status, 'title': meta.title, 'chapters': len(chapters or []),
            'video_sha256': report['source_artifact_sha256']['video.mp4']}


def finalize_release(candidate_dir: Path, out_dir: Path, *, owner_approval_statement: str,
                     contains_synthetic_media: bool, video_sha256: str) -> dict:
    """Create the hashed release only after the owner approved this exact video.

    ``video_sha256`` must match the candidate's video, so approval of one file can never
    be applied to a different render.
    """
    candidate_dir = Path(candidate_dir)
    statement = ' '.join(owner_approval_statement.split())
    if len(statement) < 10:
        raise LessonReleaseError('A written owner approval statement is required')
    report = json.loads((candidate_dir / 'quality_report.json').read_text(encoding='utf-8'))
    if not report.get('passed') or report.get('blocking'):
        raise LessonReleaseError('Candidate has blocking quality findings')
    if _sha(candidate_dir / 'video.mp4') != video_sha256.strip().lower():
        raise LessonReleaseError('Approved video hash does not match the candidate video')
    meta = ReleaseMetadata.model_validate_json((candidate_dir / 'metadata.json').read_text(encoding='utf-8'))
    meta.contains_synthetic_media = bool(contains_synthetic_media)
    review = candidate_dir.parent / (candidate_dir.name + '_editorial_review.json')
    review.write_text(json.dumps({
        'gate_passed': True,
        'gate_basis': 'manual source audit in content/<lesson>/sources.md; not the automated VerificationGate',
        'human_reviewed': True,
        'quality_passed': True,
        'reviewed_by': 'channel owner',
        'owner_statement': statement,
        'approved_video_sha256': video_sha256.strip().lower(),
        'recorded_at': datetime.now(timezone.utc).isoformat(),
    }, indent=2), encoding='utf-8')
    manifest = build_release(out_dir, candidate_dir / 'video.mp4', candidate_dir / 'thumbnail.jpg', meta,
                             editorial_report=review, caption_file=candidate_dir / 'captions.srt',
                             quality_report=report)
    return manifest


def zip_folder(folder: Path, zip_path: Path) -> Path:
    folder, zip_path = Path(folder), Path(zip_path)
    with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_STORED) as archive:
        for path in sorted(folder.iterdir()):
            if path.is_file():
                archive.write(path, arcname=path.name)
    return zip_path


def safe_extract(zip_path: Path, dest: Path) -> Path:
    """Extract a flat release zip; rejects paths, links and unexpected nesting."""
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=False)
    with zipfile.ZipFile(zip_path) as archive:
        for info in archive.infolist():
            name = info.filename
            if '/' in name or '\\' in name or name in ('', '.', '..') or name.startswith('.'):
                raise LessonReleaseError('Unsafe entry in release zip: ' + repr(name))
            if (info.external_attr >> 16) & 0o170000 == 0o120000:
                raise LessonReleaseError('Symbolic links are not allowed in release zips')
        archive.extractall(dest)
    return dest
