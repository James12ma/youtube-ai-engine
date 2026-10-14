from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Literal

class RecordedChapter(BaseModel):
    name: str
    start_s: float
    end_s: float

class RecordedSession(BaseModel):
    video_path: str
    width: int
    height: int
    duration_s: float
    chapters: list[RecordedChapter]

class NarrationSegment(BaseModel):
    text: str
    audio_path: str
    duration_s: float
    alignment: Literal['estimated','forced-aligned'] = 'estimated'

class NarrationResult(BaseModel):
    segments: list[NarrationSegment]
    total_duration_s: float
    backend: str

class EvidencePoint(BaseModel):
    label: str
    value: float
    unit: str
    source_url: str
    source_id: str
    source_snippet: str
    claim_id: str

class EvidenceDataset(BaseModel):
    title: str
    y_axis_label: str
    points: list[EvidencePoint] = Field(min_length=1)

class EditPlan(BaseModel):
    scene_index: int
    source_path: str
    start_s: float = 0.0
    duration_s: float = Field(gt=0)
    transition: Literal['fade','smoothleft','wipeleft'] = 'fade'
    overlap_s: float = Field(default=0.35, ge=0, le=1)
    zoom: float = Field(default=1.0, ge=1.0, le=1.35)
    highlight_rect: list[int] | None = None

class QCReport(BaseModel):
    passed: bool
    duration_s: float
    width: int
    height: int
    video_codec: str
    audio_codec: str
    audio_lufs: float
    audio_true_peak: float
    silence_ratio: float
    black_ratio: float
    caption_coverage: float
    warnings: list[str] = []
    failures: list[str] = []
