"""One reusable pre-packaging quality check for every video.

Blocking gates and advisory scores are kept in separate fields and are never mixed:
``blocking`` stops packaging; everything under ``advisory`` is information for the
owner's review and cannot change the outcome. Which project-policy rules block is
set by :class:`channel.packaging_lint.QualityPolicy` (advisory by default).
"""
from __future__ import annotations

from pathlib import Path
from typing import Mapping, Sequence

from pipeline.hook_score import score_hook
from pipeline.models import ScriptArtifact

from .chapters import Chapter, format_chapters, normalize_timeline, validate_chapters
from .packaging_lint import QualityPolicy, lint_packaging


class QualityGateError(ValueError):
    def __init__(self, report: dict):
        self.report = report
        super().__init__('Packaging quality gate failed: ' + '; '.join(report['blocking']))


def _fmt(f) -> str:
    return f'[{f.source}] {f.code}: {f.message}'


def evaluate_release_quality(script: ScriptArtifact, *, title: str | None = None,
                             thumbnail_text: str | None,
                             timeline: Sequence[Mapping] | None = None,
                             video_duration_s: float | None = None,
                             policy: QualityPolicy | None = None) -> tuple[dict, list[Chapter] | None]:
    """Return ``(report, chapters)``. ``report['passed']`` reflects blocking checks only.

    ``chapters`` is None when no timeline was given, or when the chapters are invalid and
    the policy only warns (they are then left out of the description rather than published broken).
    """
    policy = policy or QualityPolicy()
    final_title = ' '.join((title or script.title).split())
    packaging = lint_packaging(final_title, thumbnail_text, policy)
    blocking = [_fmt(f) for f in packaging.blocking]
    advice = [_fmt(f) for f in packaging.advisories]

    chapters = None
    chapter_section: dict = {'provided': False}
    if timeline is not None:
        chapters = normalize_timeline(timeline, video_duration_s=video_duration_s)
        check = validate_chapters(chapters, video_duration_s=video_duration_s)
        chapter_section = {'provided': True, **check.model_dump(), 'block': format_chapters(chapters)}
        problems = ['[youtube] chapters: ' + e for e in check.errors]
        if policy.invalid_chapters_rule == 'block':
            blocking.extend(problems)
        elif problems:
            advice.extend(problems)
            advice.append('[project_policy] chapters: invalid chapters omitted from the description')
            chapters = None
        if not check.final_chapter_checked:
            advice.append('[project_policy] chapters: no real video duration available, so the final '
                          'chapter length is unverified; pass --video')
    else:
        advice.append('[project_policy] chapters: none provided; pass the render report so chapters are '
                      'validated and added to the description')

    hook = score_hook(script.hook)
    report = {
        'passed': not blocking,
        'blocking': blocking,
        'title': final_title,
        'thumbnail_text': packaging.thumbnail_text,
        'policy': policy.model_dump(),
        'chapters': chapter_section,
        'advisory': {
            'note': 'Advisory only. These never block, reject or retry anything. '
                    'Items tagged project_policy are LogicScript preferences, not YouTube requirements.',
            'packaging': advice,
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
