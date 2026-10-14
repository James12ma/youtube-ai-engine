"""Deterministic SEO from source-backed and approved materials, never fabricated claims."""
from __future__ import annotations
import re
from urllib.parse import urlparse
from pydantic import BaseModel, Field
from typing import Optional
from pipeline.models import ScriptArtifact, ResearchArtifact
from verification.models import VerificationGateReport

class ReleaseMetadata(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1, max_length=5000)
    tags: list[str] = Field(default_factory=list, max_length=25)
    category_id: str = '27'  # Education
    language: str = 'en'
    made_for_kids: bool = False
    contains_synthetic_media: Optional[bool] = None  # owner MUST decide before approval/upload


def generate_metadata(script: ScriptArtifact, research: ResearchArtifact, gate: VerificationGateReport) -> ReleaseMetadata:
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
    desc = ('Learn how small businesses can evaluate AI automation workflows.\n\n'
            + 'Topics covered: '+', '.join(s.heading for s in script.sections[:8])
            + '\n\nSources referenced in the research:\n'+source_lines
            + '\n\nEducational demonstration. Verify services and results independently.\n'
            + 'Original narration and visuals; human editorial review required.')
    if len(desc)>5000:
        raise ValueError('Citation description too long')
    stop = {'with','your','from','that','this','what','when','where','into','about','these','those','their','small','business','how','the','and','for','are','you'}
    words = re.findall(r'[A-Za-z][A-Za-z0-9-]{2,}', script.topic+' '+script.title)
    tags = []
    for term in ['AI automation','small business automation', *words]:
        key=term.casefold()
        if key not in stop and key not in (t.casefold() for t in tags): tags.append(term)
    return ReleaseMetadata(title=title, description=desc, tags=tags[:15])
