from __future__ import annotations
from typing import List, Literal
from pydantic import BaseModel, Field
class Source(BaseModel):
    source_id: str
    url: str
    title: str
    retrieved_at: str
    text: str
class ClaimProposal(BaseModel):
    text: str
    source_id: str
    supporting_snippet: str
class ResearchOutput(BaseModel):
    claims: List[ClaimProposal] = Field(default_factory=list)
class ScriptSection(BaseModel):
    heading: str
    narration: str
    on_screen_text: str = ''
    claim_ids: List[str] = Field(default_factory=list)
class ScriptOutput(BaseModel):
    title: str
    hook: str
    sections: List[ScriptSection]
    cta: str
class Scene(BaseModel):
    index: int
    section_index: int
    start_s: float
    end_s: float
    visual_type: Literal['screen_recording','diagram','text_overlay','chart','broll']
    instruction: str
    claim_ids: List[str] = Field(default_factory=list)
class StoryboardOutput(BaseModel):
    scenes: List[Scene]
class VerifiedClaim(BaseModel):
    id: str
    text: str
    source_ids: List[str]
    supporting_snippets: List[str]
class ResearchArtifact(BaseModel):
    topic: str
    sources: List[Source]
    claims: List[VerifiedClaim]
    rejected_claims: List[dict]
    retrieved_at: str
class VerificationArtifact(BaseModel):
    evidence_level: Literal["excerpt_and_numeric_consistency_only"] = "excerpt_and_numeric_consistency_only"
    ready_for_publication: Literal[False] = False
    topic: str
    verified: List[VerifiedClaim]
    rejected: List[dict]
    pass_rate: float
    verified_at: str
class ScriptArtifact(BaseModel):
    requires_editorial_review: bool = True
    topic: str
    title: str
    hook: str
    sections: List[ScriptSection]
    cta: str
    duration_s: float
    word_count: int
    verified_at: str
