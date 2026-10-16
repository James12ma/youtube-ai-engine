from __future__ import annotations
from typing import List, Literal
from pydantic import BaseModel, Field, field_validator
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
# Free models often vary spelling/case of the same visual category. Map
# only unambiguous synonyms; anything else still fails validation.
_VISUAL_SYNONYMS = {
    'screenrecording':'screen_recording','screencast':'screen_recording','screencapture':'screen_recording','screen':'screen_recording',
    'diagram':'diagram','animation':'diagram','animateddiagram':'diagram','flowchart':'diagram','illustration':'diagram',
    'textoverlay':'text_overlay','text':'text_overlay','title':'text_overlay','titlecard':'text_overlay','overlay':'text_overlay',
    'chart':'chart','graph':'chart','datachart':'chart',
    'broll':'broll','stockfootage':'broll','footage':'broll'}
class Scene(BaseModel):
    index: int
    section_index: int
    start_s: float
    end_s: float
    visual_type: Literal['screen_recording','diagram','text_overlay','chart','broll']
    instruction: str
    claim_ids: List[str] = Field(default_factory=list)
    search_terms: str = ''  # photo scenes: short English subject name used to find a free-licensed photo
    @field_validator('visual_type', mode='before')
    @classmethod
    def _normalize_visual_type(cls, value):
        if isinstance(value, str):
            key=''.join(ch for ch in value.lower() if ch.isalnum())
            return _VISUAL_SYNONYMS.get(key, value)
        return value
    @field_validator('claim_ids', mode='before')
    @classmethod
    def _none_claims_to_empty(cls, value):
        return [] if value is None else value
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
    language: str = 'en'
    topic: str
    title: str
    hook: str
    sections: List[ScriptSection]
    cta: str
    duration_s: float
    word_count: int
    verified_at: str
