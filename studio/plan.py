"""Video plan: what the Director produces and the renderer consumes.

A plan is a list of beats. Each beat is one piece of narration (usually one sentence) and the shots
that show it. Each shot is a built-in scene or AI-written scene code, with cues: named moments tied to a
phrase spoken in that beat. Keywords to highlight in captions are wrapped in *asterisks* in the narration.
"""
from __future__ import annotations

import re
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

Format = Literal['vertical', 'horizontal', 'square']


class Cue(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    phrase: str = Field(default='', max_length=120, description='Words from this beat\'s narration; empty = start of shot')
    args: dict[str, Any] = Field(default_factory=dict)


class Headline(BaseModel):
    lines: list[str] = Field(min_length=1, max_length=3)
    accent: Optional[int] = Field(default=None, description='index of the line shown in the accent colour')
    pills: list[str] = Field(default_factory=list, max_length=2)
    source: str = ''


class Shot(BaseModel):
    scene: str = Field(description="built-in scene name, or 'custom' with code")
    code: str = Field(default='', description='JavaScript defining function scene(S){...; return t=>{...}} for custom scenes')
    params: dict[str, Any] = Field(default_factory=dict)
    starts_at: str = Field(default='', max_length=120, description='phrase where this shot starts; empty for the first shot of a beat')
    cues: list[Cue] = Field(default_factory=list)
    headline: Optional[Headline] = None
    camera: Literal['push', 'pull', 'pan', 'drift', 'none'] = 'push'
    transition: Literal['push', 'slide', 'fade'] = 'push'
    layout: Literal['art', 'full'] = 'art'

    @model_validator(mode='after')
    def _code_for_custom(self):
        if self.scene == 'custom' and 'function scene' not in self.code:
            raise ValueError('custom scenes need code defining function scene(S)')
        return self


class Beat(BaseModel):
    narration: str = Field(min_length=1, max_length=600)
    shots: list[Shot] = Field(min_length=1, max_length=4)


class VideoPlan(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    format: Format = 'vertical'
    style: str | dict = 'explainer-dark'
    language: str = 'en'
    voice: str = ''
    brand: str = ''
    music: str = 'soft'
    beats: list[Beat] = Field(min_length=1, max_length=60)

    @field_validator('beats')
    @classmethod
    def _non_empty(cls, v):
        if not any(b.narration.strip() for b in v):
            raise ValueError('plan has no narration')
        return v


KEY_RE = re.compile(r'\*([^*]+)\*')


def spoken(text: str) -> str:
    """Narration as it is spoken (keyword markers removed)."""
    return ' '.join(KEY_RE.sub(r'\1', text).split())


def keywords(text: str) -> set[str]:
    return {w.lower() for m in KEY_RE.findall(text) for w in re.findall(r"[A-Za-z0-9'$%.,-]+", m)}
