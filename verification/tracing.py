"""Trace *accepted* claims to the exact evidence actually accepted by the gate."""
from __future__ import annotations
import re
from typing import Sequence
from pipeline.models import ScriptArtifact, Source, VerificationArtifact
from .models import ClaimVerdict, TracedClaim, TraceabilityReport
from .numbers import numbers

_NUMERIC_RE=re.compile(r'(?:\d+(?:\.\d+)?\s*(?:%|users|customers|hours|minutes|dollars|percent|savings|days|weeks|months|years)|\$\s*\d|\b(?:19|20)\d{2}\b)',re.I)

def build_trace(script:ScriptArtifact, verification:VerificationArtifact,
                sources:Sequence[Source], verdicts:Sequence[ClaimVerdict]) -> TraceabilityReport:
    by_claim={c.id:c for c in verification.verified}
    by_source={s.source_id:s for s in sources}
    by_verdict={v.claim_id:v for v in verdicts}
    citations=[]; unverified=[]; uncited_numeric=[]
    for index,section in enumerate(script.sections):
        for cid in section.claim_ids:
            claim=by_claim.get(cid); verdict=by_verdict.get(cid)
            if not claim or not verdict or not verdict.accepted or not verdict.supporting_source_ids:
                if cid not in unverified: unverified.append(cid)
                continue
            sids=[sid for sid in verdict.supporting_source_ids if sid in by_source and sid in claim.source_ids]
            if not sids or len(sids)!=len(set(verdict.supporting_source_ids)):
                if cid not in unverified: unverified.append(cid)
                continue
            snippets=[claim.supporting_snippets[claim.source_ids.index(sid)] for sid in sids]
            citations.append(TracedClaim(section_index=index,claim_id=cid,source_ids=sids,
                          source_urls=[by_source[sid].url for sid in sids],supporting_snippets=snippets,
                          best_label=verdict.best_label,best_credibility=verdict.best_credibility))
        spoken_numbers = numbers(section.narration)
        if _NUMERIC_RE.search(section.narration) and not section.claim_ids:
            uncited_numeric.append(index)
        elif spoken_numbers:
            supported=set()
            for cid in section.claim_ids:
                v=by_verdict.get(cid); c=by_claim.get(cid)
                if v and v.accepted and c:
                    supported |= numbers(c.text)
                    for sid in v.supporting_source_ids:
                        if sid in c.source_ids:
                            supported |= numbers(c.supporting_snippets[c.source_ids.index(sid)])
            if not spoken_numbers.issubset(supported) and index not in uncited_numeric:
                uncited_numeric.append(index)
    return TraceabilityReport(citations=citations,
                              uncited_numeric_sections=uncited_numeric,
                              unverified_cited_claims=unverified)
