"""One reusable pre-packaging quality check for every video.

Blocking gates and advisory scores are kept in separate fields and are never mixed:
``blocking`` stops packaging; everything under ``advisory`` is information for the
owner's review and cannot change the outcome.
"""
from __future__ import annotations

from pathlib import Path
from typing import Mapping, Sequence

from pipeline.hook_score import score_hook
from pipeline.models import ScriptArtifact

from .chapters import Chapter, format_chapters, normalize_timeline, validate_chapters
from .packaging_lint import lint_packaging


class QualityGateError(ValueError):
    def __init__(self, report: dict):
        self.report = report
        super().__init__('Packaging quality gate failed: ' + '; '.join(report['blocking']))


def evaluate_release_quality(script: ScriptArtifact, *, title: str | None = None,
                             thumbnail_text: str | None,
                             timeline: Sequence[Mapping] | None = None,
                             video_duration_s: float | None = None) -> tuple[dict, list[Chapter] | None]:
    """Return ``(report, chapters)``. ``report['passed']`` reflects blocking checks only."""
    final_title = ' '.join((title or script.title).split())
    packaging = lint_packaging(final_title, thumbnail_text)
    blocking = [f'{f.code}: {f.message}' for f in packaging.blocking]
    if thumbnail_text is None:
        blocking.append('thumbnail-text: unknown; pass the exact thumbnail text so the '
                        'title/thumbnail pairing can be checked')

    chapters = None
    chapter_section: dict = {'provided': False}
    if timeline is not None:
        chapters = normalize_timeline(timeline, video_duration_s=video_duration_s)
        check = validate_chapters(chapters, video_duration_s=video_duration_s)
        chapter_section = {'provided': True, **check.model_dump(), 'block': format_chapters(chapters)}
        blocking.extend('chapters: ' + e for e in check.errors)

    packaging_advice = [f'{f.code}: {f.message}' for f in packaging.advisories]
    if timeline is None:
        packaging_advice.append('chapters: none provided; pass the render report so chapters are '
                                'validated and added to the description')
    hook = score_hook(script.hook)
    report = {
        'passed': not blocking,
        'blocking': blocking,
        'title': final_title,
        'thumbnail_text': thumbnail_text,
        'chapters': chapter_section,
        'advisory': {
            'note': 'Advisory only. These scores never block, reject or retry anything.',
            'packaging': packaging_advice,
            'mobile_preview': packaging.mobile_preview,
            'hook': hook.model_dump(),
        },
    }
    return report, chapters


def require_quality(report: dict) -> None:
    if report['blocking']:
        raise QualityGateError(report)


def probe_duration(video: Path) -> float | None:
    from .release import _ffprobe
    try:
        return float(_ffprobe(Path(video)).get('format', {}).get('duration'))
    except Exception:
        return None
