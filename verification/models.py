from __future__ import annotations
from enum import Enum
from typing import List
from pydantic import BaseModel, Field

class EntailmentLabel(str, Enum):
    ENTAILMENT = 'entailment'
    NEUTRAL = 'neutral'
    CONTRADICTION = 'contradiction'

class EntailmentJudgment(BaseModel):
    claim_id: str
    source_id: str
    label: EntailmentLabel
    confidence: float = Field(ge=0, le=1)
    reasoning: str = ''
class EntailmentBatch(BaseModel):
    judgments: List[EntailmentJudgment] = Field(default_factory=list)
class CredibilityAssessment(BaseModel):
    source_id: str
    domain: str
    tier: str
    score: float = Field(ge=0, le=1)
    signals: List[str] = Field(default_factory=list)
class ContradictionPair(BaseModel):
    claim_id_a: str
    claim_id_b: str
    explanation: str
class ContradictionReport(BaseModel):
    pairs: List[ContradictionPair] = Field(default_factory=list)
class ClaimVerdict(BaseModel):
    claim_id: str
    text: str
    accepted: bool
    reason: str
    best_label: EntailmentLabel
    best_confidence: float
    best_credibility: float
    weighted_score: float
    supporting_source_ids: List[str] = Field(default_factory=list)
class TracedClaim(BaseModel):
    section_index: int
    claim_id: str
    source_ids: List[str]
    source_urls: List[str]
    supporting_snippets: List[str]
    best_label: EntailmentLabel
    best_credibility: float
class TraceabilityReport(BaseModel):
    citations: List[TracedClaim] = Field(default_factory=list)
    uncited_numeric_sections: List[int] = Field(default_factory=list)
    unverified_cited_claims: List[str] = Field(default_factory=list)
class VerificationGateReport(BaseModel):
    topic: str
    verdicts: List[ClaimVerdict]
    credibility: List[CredibilityAssessment]
    contradictions: ContradictionReport
    traceability: TraceabilityReport
    accepted_count: int
    rejected_count: int
    verified_at: str
