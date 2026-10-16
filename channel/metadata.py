"""Deterministic SEO from source-backed and approved materials, never fabricated claims."""
from __future__ import annotations
import re
from urllib.parse import urlparse
from pydantic import BaseModel, Field
from typing import Optional, Sequence
from pipeline.models import ScriptArtifact, ResearchArtifact
from verification.models import VerificationGateReport
from .chapters import Chapter, format_chapters, validate_chapters

class ReleaseMetadata(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1, max_length=5000)
    tags: list[str] = Field(default_factory=list, max_length=25)
    category_id: str = '27'  # Education
    language: str = 'en'
    made_for_kids: bool = False
    contains_synthetic_media: Optional[bool] = None  # owner MUST decide before approval/upload


def generate_metadata(script: ScriptArtifact, research: ResearchArtifact, gate: VerificationGateReport,
                      *, chapters: Optional[Sequence[Chapter]] = None,
                      video_duration_s: Optional[float] = None) -> ReleaseMetadata:
    if script.topic != research.topic or gate.topic != script.topic:
        raise ValueError('Artifact topics mismatch')
    accepted = {v.claim_id for v in gate.verdicts if v.accepted}
    if not accepted or gate.contradictions.pairs or gate.traceability.unverified_cited_claims:
        raise ValueError('Verification gate is incomplete or failed')
    cited = {c for sec in script.sections for c in sec.claim_ids}
    if cited - accepted:
        raise ValueError('Script cites rejected claims')
    sources = {s.source_id:s for s in research.sources}
    referenced = {}
    for c in gate.traceability.citations:
        if c.claim_id in accepted:
            for sid in c.source_ids:
                if sid in sources:
                    referenced[sid] = sources[sid].url
    if not referenced:
        raise ValueError('No traceable source citations')
    for url in referenced.values():
        p = urlparse(url)
        if p.scheme != 'https' or not p.hostname:
            raise ValueError('Invalid citation URL')
    title = ' '.join(script.title.split())[:100]
    # Source URLs are provenance only. Do not claim they are independent proof of truth.
    source_lines = '\n'.join('- '+u for u in dict.fromkeys(referenced.values()))
    chapter_block = ''
    if chapters is not None:
        result = validate_chapters(chapters, video_duration_s=video_duration_s)
        if not result.passed:
            raise ValueError('Chapters invalid for YouTube: ' + '; '.join(result.errors))
        chapter_block = 'Chapters:\n' + format_chapters(chapters) + '\n\n'
    t = _TEXT.get(script.language, _TEXT['en'])
    if chapter_block and script.language != 'en':
        chapter_block = chapter_block.replace('Chapters:', t['chapters'], 1)
    desc = (description_intro(script) + '\n\n'
            + chapter_block
            + t['covers'] + '\n' + '\n'.join('- '+h for h in _headings(script)[:10])
            + '\n\n' + t['sources'] + '\n'+source_lines
            + '\n\n' + t['footer'])
    desc = _youtube_safe(desc)
    if len(desc.encode('utf-8'))>5000:  # YouTube's limit is 5000 bytes
        raise ValueError('Citation description too long')
    return ReleaseMetadata(title=_youtube_safe(title), description=desc, tags=derive_tags(script),
                           language=script.language)


def _youtube_safe(text: str) -> str:
    """YouTube rejects < and > in titles, descriptions and tags."""
    return text.replace('<', '').replace('>', '')


_TAG_STOP = {'with','your','from','that','this','what','when','where','into','about','these','those',
             'their','how','the','and','for','are','you','why','can','will','its','not','but','all'}


def _headings(script: ScriptArtifact) -> list[str]:
    return [' '.join(s.heading.split()) for s in script.sections if s.heading.strip()]


def _first_sentence(text: str, limit: int = 160) -> str:
    text = ' '.join(text.split())
    m = re.match(r'(.+?[.!?])(\s|$)', text)
    sentence = m.group(1) if m else text
    if len(sentence) > limit:
        sentence = sentence[:limit].rsplit(' ', 1)[0].rstrip(',;:') + '...'
    return sentence


def _join(items: list[str], conj: str = ' and ') -> str:
    items = [i for i in items if i]
    if len(items) <= 1:
        return ''.join(items)
    return ', '.join(items[:-1]) + conj + items[-1]


def _soft_lower(heading: str) -> str:
    """Lower-case a heading's first letter unless it starts an acronym (AI, CSV)."""
    if len(heading) > 1 and heading[1].isupper():
        return heading
    return heading[:1].lower() + heading[1:]


_TEXT = {
    'en': {'explains': 'This video explains', 'covers': 'What this video covers:',
           'sources': 'Sources referenced in the research:', 'chapters': 'Chapters:',
           'footer': 'Educational demonstration. Verify services and results independently.\n'
                     'Original narration and visuals; human editorial review required.'},
    'es': {'explains': 'En este video explicamos', 'covers': 'En este video:',
           'sources': 'Fuentes oficiales consultadas:', 'chapters': 'Capítulos:',
           'footer': 'Información general y educativa; no es asesoría fiscal ni legal para su caso. '
                     'Verifique siempre en IRS.gov o con un preparador de impuestos autorizado.\n'
                     'Narración y gráficos originales; revisado por una persona antes de publicar.'},
}


def description_intro(script: ScriptArtifact) -> str:
    """Two topic-specific opening lines built only from the reviewed script.

    These are the lines shown above "...more" and in search snippets, so they are
    derived from this video's own hook, topic and section headings. Nothing is
    invented: the hook already passed the script gate (no uncited numbers).
    """
    line1 = _first_sentence(script.hook)
    topic = ' '.join(script.topic.split())
    headings = _headings(script)[:3]
    line2 = _TEXT.get(script.language, _TEXT['en'])['explains'] + ' ' + topic
    if headings:
        line2 += ': ' + _join([_soft_lower(h) for h in headings], ' y ' if script.language == 'es' else ' and ')
    line2 = line2.rstrip('.') + '.'
    return line1 + '\n' + line2


def derive_tags(script: ScriptArtifact, limit: int = 15) -> list[str]:
    """Disambiguation tags from this video's own topic, title and headings (max 15)."""
    tags: list[str] = []
    def add(term: str):
        term = _youtube_safe(' '.join(term.split()).strip(' .,:;!?'))
        key = term.casefold()
        if (len(term) >= 3 and len(term) <= 30 and key not in _TAG_STOP
                and key not in (t.casefold() for t in tags)):
            tags.append(term)
    add(script.topic)
    for heading in _headings(script):
        if len(heading.split()) <= 4:
            add(heading)
    for word in re.findall(r'[A-Za-z][A-Za-z0-9-]{2,}', script.topic + ' ' + script.title):
        add(word)
    total = 0; kept = []
    for t in tags[:limit]:
        if total + len(t) > 450:  # YouTube caps tags at 500 characters in total
            break
        kept.append(t); total += len(t) + 1
    return kept
