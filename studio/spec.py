"""Cinematic Production Spec: the one contract between Director, asset producers and Editor.

A film is a list of shots. Every shot covers a contiguous span of narration words, renders with
exactly one registered technique, and lists the story beats (who does what to which object, and
how that object's state changes) that must be visible inside that span. Validation fails closed:
an unknown technique, an uncovered word, a beat outside its words, or a broken state chain blocks
rendering instead of falling back to a generic visual.
"""
from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from .capabilities import REGISTRY, TechniqueError, validate_params

WORD_RE = re.compile(r"[\w$€£%]+(?:['’.,:][\w]+)*")


def tokenize(text: str) -> list[str]:
    """Narration words, in order; punctuation is not a word. Shared by Director, voice and editor."""
    return WORD_RE.findall(text)


class Format(BaseModel):
    width: int = 1080
    height: int = 1920
    fps: int = 30

    @model_validator(mode="after")
    def _sane(self):
        if not (320 <= self.width <= 3840 and 320 <= self.height <= 3840 and self.fps in (24, 25, 30, 60)):
            raise ValueError("format must be 320..3840 px per side at 24/25/30/60 fps")
        return self


class Entity(BaseModel):
    """Anything the audience must recognise across shots: a person, an object, a place, a UI, data."""
    kind: Literal["character", "prop", "location", "ui", "data", "organization"]
    name: str
    appearance: str = Field("", description="Stable visual description reused in every generation prompt")
    seed: int | None = Field(None, description="Generation seed kept constant for consistency")
    reference_asset: str | None = Field(None, description="Asset id of a reference image (identity lock)")
    initial_state: str | None = None


class Beat(BaseModel):
    """One visible event. `at_word` is the narration word index where it must be on screen."""
    action: str
    actor: str | None = None
    object: str | None = None
    at_word: int
    state_before: str | None = None
    state_after: str | None = None
    note: str = ""


class Camera(BaseModel):
    move: Literal["static", "push_in", "pull_out", "pan_left", "pan_right", "tilt_up", "tilt_down",
                  "drift", "orbit", "whip"] = "push_in"
    intensity: float = Field(0.08, ge=0, le=0.6, description="Fraction of frame travelled over the shot")
    focus: tuple[float, float] = (0.5, 0.5)


class Transition(BaseModel):
    kind: Literal["cut", "whip_blur", "zoom_through", "match", "dip_white", "dip_black", "slide_up", "blur"] = "cut"
    frames: int = Field(0, ge=0, le=20)
    match_entity: str | None = Field(None, description="Entity that stays in place across a match cut")


class TextOverlay(BaseModel):
    """Word-synced kinetic type for this shot. Words appear on their spoken frame."""
    mode: Literal["none", "words", "headline", "stack", "center_word"] = "words"
    emphasis: list[int] = Field(default_factory=list, description="Word indices set large in the accent face")
    mute: list[int] = Field(default_factory=list, description="Word indices set in the secondary grey")
    position: Literal["top", "center", "bottom"] = "top"
    show_words: tuple[int, int] | None = Field(None, description="Subset of the shot's words to display")


class SfxCue(BaseModel):
    at_word: int
    sound: Literal["tap", "click", "whoosh", "pop", "ding", "thud", "ring", "type", "swoosh_up"]
    gain: float = 0.6


class Shot(BaseModel):
    id: str
    scene: str = Field(..., description="Scene id, groups shots that share a world/location")
    world: Literal["story", "explain", "screen", "map", "footage"] = "story"
    purpose: str = Field(..., description="What the audience must understand from this shot")
    words: tuple[int, int] = Field(..., description="Inclusive narration word range covered")
    technique: str
    params: dict[str, Any] = Field(default_factory=dict)
    beats: list[Beat] = Field(default_factory=list)
    entities: list[str] = Field(default_factory=list)
    camera: Camera = Field(default_factory=Camera)
    transition_in: Transition = Field(default_factory=Transition)
    text: TextOverlay = Field(default_factory=TextOverlay)
    sfx: list[SfxCue] = Field(default_factory=list)


class Narration(BaseModel):
    text: str
    language: Literal["en", "es", "fr", "ht", "pt"] = "en"
    voice: str = ""
    audio: str | None = Field(None, description="Asset id of the rendered voice track")
    word_times: list[tuple[float, float]] | None = Field(None, description="[start, end] seconds per word")


class AssetRequest(BaseModel):
    """How to produce an asset the shots reference. Prompts are written for the generator, not the viewer."""
    kind: Literal["image", "video", "music"]
    prompt: str
    entities: list[str] = Field(default_factory=list, description="Entities whose appearance is appended for consistency")
    source_image: str | None = Field(None, description="For video: asset id of the start image (image-to-video)")
    seconds: float = Field(5.0, gt=0, le=20)


class Music(BaseModel):
    asset: str | None = None
    gain_db: float = -20.0
    duck_db: float = -8.0


class FilmSpec(BaseModel):
    version: Literal[1] = 1
    id: str
    title: str
    format: Format = Field(default_factory=Format)
    style: Literal["editorial_two_world", "documentary", "screen_tutorial", "clean_explainer"] = "editorial_two_world"
    narration: Narration
    entities: dict[str, Entity] = Field(default_factory=dict)
    assets: dict[str, AssetRequest] = Field(default_factory=dict)
    shots: list[Shot]
    music: Music = Field(default_factory=Music)
    tail_seconds: float = Field(0.8, ge=0, le=5)
    capability_gaps: list[str] = Field(default_factory=list,
                                       description="Story needs the system cannot render; non-empty blocks rendering")

    @property
    def tokens(self) -> list[str]:
        return tokenize(self.narration.text)


class SpecError(ValueError):
    def __init__(self, problems: list[str]):
        super().__init__("; ".join(problems))
        self.problems = problems


def validate(spec: FilmSpec, *, require_timing: bool = False) -> list[str]:
    """Return warnings; raise SpecError listing every blocking problem."""
    problems: list[str] = []
    warnings: list[str] = []
    n = len(spec.tokens)
    if n == 0:
        problems.append("narration is empty")
    if spec.capability_gaps:
        problems += [f"capability gap: {g}" for g in spec.capability_gaps]
    expected = 0
    states: dict[str, str | None] = {k: e.initial_state for k, e in spec.entities.items()}
    seen_ids: set[str] = set()
    for shot in spec.shots:
        where = f"shot {shot.id}"
        if shot.id in seen_ids:
            problems.append(f"{where}: duplicate id")
        seen_ids.add(shot.id)
        a, b = shot.words
        if a != expected:
            problems.append(f"{where}: starts at word {a}, expected {expected} (words must be covered contiguously)")
        if b < a or b >= n:
            problems.append(f"{where}: word range {shot.words} outside 0..{n - 1}")
        expected = b + 1
        try:
            validate_params(shot.technique, shot.params)
        except TechniqueError as e:
            problems.append(f"{where}: {e}")
        else:
            if shot.world not in REGISTRY[shot.technique].worlds:
                problems.append(f"{where}: technique {shot.technique} does not render the '{shot.world}' world")
        for key in ("image", "video", "asset", "background_image"):
            ref = shot.params.get(key)
            if ref and ref not in spec.assets:
                problems.append(f"{where}: asset '{ref}' has no AssetRequest (how would it be produced?)")
        for ent in shot.entities:
            if ent not in spec.entities:
                problems.append(f"{where}: unknown entity '{ent}'")
        for beat in shot.beats:
            if not a <= beat.at_word <= b:
                problems.append(f"{where}: beat '{beat.action}' at word {beat.at_word} is outside its words {shot.words}")
            for ref in (beat.actor, beat.object):
                if ref and ref not in spec.entities:
                    problems.append(f"{where}: beat '{beat.action}' references unknown entity '{ref}'")
            if beat.object and beat.state_after:
                current = states.get(beat.object)
                if beat.state_before is not None and current is not None and beat.state_before != current:
                    problems.append(f"{where}: {beat.object} is '{current}' but beat '{beat.action}' expects '{beat.state_before}'")
                states[beat.object] = beat.state_after
        for i in shot.text.emphasis + shot.text.mute:
            if not a <= i <= b:
                problems.append(f"{where}: text styling word {i} outside the shot")
        for cue in shot.sfx:
            if not a <= cue.at_word <= b:
                problems.append(f"{where}: sfx at word {cue.at_word} outside the shot")
        if not shot.beats and shot.world in ("story", "screen"):
            warnings.append(f"{where}: no visible beat; make sure the picture still explains the words")
    for aid, req in spec.assets.items():
        for ent in req.entities:
            if ent not in spec.entities:
                problems.append(f"asset {aid}: unknown entity '{ent}'")
        if req.kind == "video" and req.source_image and req.source_image not in spec.assets:
            problems.append(f"asset {aid}: source image '{req.source_image}' is not requested")
    if n and expected != n:
        problems.append(f"words {expected}..{n - 1} are not covered by any shot")
    times = spec.narration.word_times
    if require_timing:
        if not times or len(times) != n:
            problems.append(f"word timing missing or length {len(times or [])} != {n} words")
        else:
            for shot in spec.shots:
                dur = times[shot.words[1]][1] - times[shot.words[0]][0]
                if dur > 6.0:
                    warnings.append(f"shot {shot.id}: {dur:.1f}s long; reference pacing is ~2s per shot")
    if problems:
        raise SpecError(problems)
    return warnings
