from __future__ import annotations
from pydantic import BaseModel, Field

class WordTiming(BaseModel):
    text: str
    start_s: float = Field(ge=0)
    end_s: float = Field(gt=0)

class TTSResult(BaseModel):
    audio_path: str
    duration_s: float
    word_timings: list[WordTiming]
    voice: str
    backend: str

class RenderConfig(BaseModel):
    width: int = Field(default=1920, ge=320, le=3840)
    height: int = Field(default=1080, ge=180, le=2160)
    fps: int = Field(default=30, ge=10, le=60)
    crf: int = Field(default=22, ge=16, le=35)
    preset: str = 'ultrafast'
    caption_max_chars: int = 32
    caption_font: str = 'DejaVu Sans'
    caption_size: int = 48
    audio_lufs: float = -16.0
    audio_tp: float = -1.5
    audio_lra: float = 11.0
    require_captions: bool = True
    temp_scale: int = 1

class RenderReport(BaseModel):
    output_path: str
    duration_s: float
    width: int
    height: int
    fps: float
    video_codec: str
    audio_codec: str
    audio_lufs: float
    audio_true_peak: float
    file_size_bytes: int
    scene_count: int
    caption_count: int
    caption_file: str
    tts_backend: str
    ready_for_publication: bool = False
    warnings: list[str] = Field(default_factory=list)
