"""Fail-closed claim gate. Advisory LLM scores are never proof of truth.

No publishing or external writes. This gate must be invoked explicitly after
script creation, BEFORE any future asset creation/publication workflow.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Sequence
from pipeline.models import ResearchArtifact, ScriptArtifact, Source, VerificationArtifact, VerifiedClaim
from .contradictions import ContradictionConfig, ContradictionDetector
from .credibility import assess_all, independent_domain
from .entailment import EntailmentConfig, EntailmentVerifier
from .errors import GateRejected
from .models import ClaimVerdict, CredibilityAssessment, EntailmentLabel, VerificationGateReport
from .tracing import build_trace
from .numbers import numbers

@dataclass
class GateConfig:
    entailment_confidence:float=0.70
    min_weighted_score:float=0.55
    min_source_credibility:float=0.40
    corroboration_bonus_per_source:float=0.05
    max_corroboration_bonus:float=0.20
    require_zero_contradictions:bool=True
    require_numeric_citations:bool=True

@dataclass
class GateOutcome:
    report:VerificationGateReport
    accepted_claims:list[VerifiedClaim]=field(default_factory=list)
    warnings:list[str]=field(default_factory=list)

def _now()->str:
    return datetime.now(timezone.utc).isoformat()

class VerificationGate:
    def __init__(self,router,config:Optional[GateConfig]=None,
                 entailment_config:Optional[EntailmentConfig]=None,
                 contradiction_config:Optional[ContradictionConfig]=None):
        self._router=router
        self._config=config or GateConfig()
        self._entailment=EntailmentVerifier(router,entailment_config)
        self._contradictions=ContradictionDetector(router,contradiction_config)

    @staticmethod
    def _check_provenance(research:ResearchArtifact,verification:VerificationArtifact,
                          script:ScriptArtifact,sources:Sequence[Source])->None:
        if not (research.topic==verification.topic==script.topic):
            raise GateRejected('Artifact topics do not match',{'topics':[research.topic,verification.topic,script.topic]})
        srcs={s.source_id:(s.url,s.text) for s in research.sources}
        supplied={s.source_id:(s.url,s.text) for s in sources}
        if len(srcs)!=len(research.sources) or len(supplied)!=len(sources) or srcs!=supplied:
            raise GateRejected('Inconsistent source evidence',{})
        claims={c.id:c for c in research.claims}
        if len(claims)!=len(research.claims):
            raise GateRejected('Duplicate claim IDs',{})
        for c in verification.verified:
            if c.id not in claims or c.model_dump()!=claims[c.id].model_dump():
                raise GateRejected('Verification artifact changed claim evidence',{'claim_id':c.id})
        for c in research.claims:
            if not c.source_ids or len(c.source_ids)!=len(set(c.source_ids)) or len(c.source_ids)!=len(c.supporting_snippets):
                raise GateRejected('Malformed claim provenance',{'claim_id':c.id})
            for sid,snippet in zip(c.source_ids,c.supporting_snippets):
                if sid not in srcs or not snippet.strip():
                    raise GateRejected('Missing claim evidence',{'claim_id':c.id,'source_id':sid})
                norm=lambda text:' '.join(text.split()).lower()
                if norm(snippet) not in norm(srcs[sid][1]):
                    raise GateRejected('Claim excerpt missing from source text',{'claim_id':c.id,'source_id':sid})

    def verify_claims(self,research:ResearchArtifact)->tuple[list[ClaimVerdict],list[CredibilityAssessment]]:
        credibility=assess_all([(s.source_id,s.url) for s in research.sources]); cred_by={c.source_id:c for c in credibility}
        source_by={s.source_id:s for s in research.sources}
        verdicts=[]
        for claim in research.claims:
            candidates=[source_by[sid] for sid in claim.source_ids if sid in source_by]
            if len(candidates)!=len(claim.source_ids):
                raise GateRejected('Invalid source IDs',{'claim_id':claim.id})
            judgments=self._entailment.judge(claim,candidates).judgments
            accepted=[]
            strongest_contradiction=0.0
            for j in judgments:
                cred=cred_by[j.source_id]
                if j.label is EntailmentLabel.CONTRADICTION and j.confidence>=self._config.entailment_confidence:
                    strongest_contradiction=max(strongest_contradiction,j.confidence)
                elif (j.label is EntailmentLabel.ENTAILMENT
                      and j.confidence>=self._config.entailment_confidence
                      and cred.score>=self._config.min_source_credibility
                      and numbers(claim.text).issubset(numbers(source_by[j.source_id].text))):
                    accepted.append((j.source_id,j.confidence,cred.score))
            if accepted:
                base=max(conf*score for sid,conf,score in accepted)
                unique_domains={independent_domain(source_by[sid].url) for sid,_,_ in accepted}
                bonus=min(self._config.max_corroboration_bonus,
                          self._config.corroboration_bonus_per_source*max(0,len(unique_domains)-1))
                weighted=min(1.0,base+bonus)
            else:
                weighted=0.0
            passed=bool(accepted) and weighted>=self._config.min_weighted_score and not strongest_contradiction
            best_conf=max([x[1] for x in accepted] or [0.0])
            best_cred=max([x[2] for x in accepted] or [0.0])
            if strongest_contradiction:
                label=EntailmentLabel.CONTRADICTION
                reason='At least one candidate source contradicts this claim'
            elif accepted:
                label=EntailmentLabel.ENTAILMENT
                reason=f'Heuristic weighted score {weighted:.3f}'
            else:
                label=EntailmentLabel.NEUTRAL
                reason='No sufficiently supported evidence'
            verdicts.append(ClaimVerdict(claim_id=claim.id,text=claim.text,accepted=passed,
                   reason=reason,best_label=label,best_confidence=max(best_conf,strongest_contradiction),
                   best_credibility=best_cred,weighted_score=weighted,
                   supporting_source_ids=[sid for sid,_,_ in accepted] if passed else []))
        return verdicts,credibility

    def run(self,research:ResearchArtifact,verification:VerificationArtifact,
            script:ScriptArtifact,sources:Sequence[Source])->GateOutcome:
        self._check_provenance(research,verification,script,sources)
        verdicts,credibility=self.verify_claims(research)
        accepted_ids={v.claim_id for v in verdicts if v.accepted}
        accepted_claims=[c for c in verification.verified if c.id in accepted_ids]
        rejected=[v for v in verdicts if not v.accepted]
        contradictions=self._contradictions.detect(accepted_claims)
        traceability=build_trace(script,verification,sources,verdicts)
        report=VerificationGateReport(topic=research.topic,verdicts=verdicts,credibility=credibility,
                contradictions=contradictions,traceability=traceability,
                accepted_count=len(accepted_claims),rejected_count=len(rejected),verified_at=_now())
        failures=[]
        if not accepted_claims: failures.append('no claims passed verification')
        if self._config.require_zero_contradictions and contradictions.pairs:
            failures.append(f'{len(contradictions.pairs)} contradiction(s) detected')
        if traceability.unverified_cited_claims:
            failures.append('script cites unverified or rejected claim ids: '+repr(traceability.unverified_cited_claims))
        if self._config.require_numeric_citations and traceability.uncited_numeric_sections:
            failures.append('numeric narration without citation: '+repr(traceability.uncited_numeric_sections))
        if self._config.require_numeric_citations and (numbers(script.hook) or numbers(script.cta)):
            failures.append('untraceable numbers in hook or CTA')
        if failures: raise GateRejected('; '.join(failures),report.model_dump())
        return GateOutcome(report=report,accepted_claims=accepted_claims,
                   warnings=['LLM entailment and domain scores are heuristic, not independent proof of truth.',
                             'Human editorial review remains required before public publishing.'])
