"""Capability Registry: the only techniques a shot may use.

`available=False` entries are known production needs that are not rendered yet. The Director can
see them and must report a capability gap instead of substituting an unrelated visual.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator


class _P(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Still25DParams(_P):
    image: str = Field(..., description="Asset id of a generated or licensed still")
    grade: Literal["none", "night", "warm", "mono", "teal_orange", "morning"] = "none"
    vignette: float = Field(0.35, ge=0, le=1)
    light_sweep: bool = False


class ClipParams(_P):
    video: str = Field(..., description="Asset id of an image-to-video clip or licensed footage")
    start_s: float = Field(0, ge=0)
    speed: float = Field(1.0, gt=0.2, le=3)
    grade: Literal["none", "night", "warm", "mono", "teal_orange", "morning"] = "none"


class UIField(_P):
    label: str
    value: str
    at_word: int | None = Field(None, description="Word where the value starts being typed (omit = already filled)")
    highlight: bool = False


class UIRow(_P):
    name: str
    role: str = ""
    tag: str = ""
    new: bool = Field(False, description="The row that arrives during the shot")


class UIScreenSpec(_P):
    """One screen of a device. Only these kinds render; fields not listed here are rejected."""
    kind: Literal["listing", "form", "confirm", "inbox", "detail", "incoming_call"]
    at_word: int | None = Field(None, description="Word where this screen appears")
    heading: str = Field("", description="listing/form/inbox: large header at the top of the screen")
    subheading: str = Field("", description="listing: search text; form: line under the header")
    title: str = ""
    company: str = Field("", description="listing: company name")
    meta: str = Field("", description="listing: one line under the title")
    cta: str = Field("", description="listing/form: button label")
    tap_cta_word: int | None = Field(None, description="form/listing: word where the button is pressed")
    body: str = Field("", description="confirm/detail: the main message line")
    fields: list[UIField] = Field(default_factory=list, description="form/detail: labelled values")
    rows: list[UIRow] = Field(default_factory=list, description="inbox: list rows")
    arrive_word: int | None = Field(None, description="inbox: word where the new row lands")
    highlight_word: int | None = Field(None, description="detail: word where the highlighted field is marked")
    caller: str = Field("", description="incoming_call: caller name")
    nav: list[str] = Field(default_factory=list, description="inbox: sidebar items")

    @model_validator(mode="after")
    def _shows_something(self):
        # A screen with nothing to draw renders as a blank white phone (tap_card run 39812806136).
        need = {"listing": self.title, "form": self.fields, "confirm": self.title or self.body, "inbox": self.rows,
                "detail": self.title or self.body or self.fields, "incoming_call": True}[self.kind]
        if not need:
            raise ValueError(f"{self.kind} screen has nothing to show (see the field descriptions)")
        return self


class UIFlowParams(_P):
    """A device whose screens change on story beats: tap, type, submit, receive, open, highlight, ring."""
    device: Literal["phone", "laptop"] = "phone"
    app_name: str = "App"
    accent: str = Field("#2f6bff", pattern=r"^#[0-9a-fA-F]{6}$")
    screens: list[UIScreenSpec] = Field(..., min_length=1, description="Ordered screens; each changes on its word")
    background: Literal["paper", "dark", "asset"] = "paper"
    background_image: str | None = None
    hand: bool = Field(True, description="Show a thumb/cursor performing the taps")
    clock: str = Field("9:41", pattern=r"^\d{1,2}:\d{2}$", description="Time shown on the device (keep story time consistent)")


class DataTransferParams(_P):
    """An object leaves a sender and arrives at a receiver; the arrival is the visible cause of the next shot."""
    packet: Literal["document", "message", "money", "photo"] = "document"
    packet_label: str = ""
    packet_note: str = Field("", description="Small line at the bottom of the packet (e.g. sender name)")
    sender_label: str
    receiver_label: str
    path: Literal["arc", "city", "network"] = "city"
    depart_word: int
    arrive_word: int


class DotsSubtractParams(_P):
    count: int = Field(28, ge=4, le=80)
    keep: int = Field(1, ge=1)
    remove_word: int


class Object3DParams(_P):
    asset: str = Field(..., description="Asset id of a pre-rendered object with alpha (Blender library)")
    caption: str = ""
    shadow: bool = True


class TitleParams(_P):
    kicker: str = ""
    background: Literal["paper", "dark"] = "paper"


@dataclass(frozen=True)
class Technique:
    name: str
    params: type[BaseModel] | None
    worlds: tuple[str, ...]
    available: bool
    renders: str


REGISTRY: dict[str, Technique] = {t.name: t for t in [
    Technique("still_2_5d", Still25DParams, ("story", "footage"), True,
              "Photoreal still with cinematic camera move, grade, vignette, optional light sweep"),
    Technique("clip", ClipParams, ("story", "footage", "screen"), True,
              "Video clip (image-to-video or licensed footage), trimmed to the narration span"),
    Technique("ui_flow", UIFlowParams, ("explain", "screen", "story"), True,
              "Phone/laptop UI whose screens change on beats with taps, typing, confirmation, inbox, call"),
    Technique("data_transfer", DataTransferParams, ("explain", "map"), True,
              "Packet travels from sender to receiver along a drawn path; arrival on a narrated word"),
    Technique("dots_subtract", DotsSubtractParams, ("explain",), True,
              "Many items around one; the rest disappear on a word (focus / removal ideas)"),
    Technique("object_3d", Object3DParams, ("explain",), True,
              "Pre-rendered 3D object on paper with soft shadow and gentle float"),
    Technique("title", TitleParams, ("explain", "story"), True,
              "Type-only beat: the narration words are the picture"),
    Technique("map_route", None, ("map",), False,
              "Globe/route capture (God's Eye capability; not yet ported into the editor)"),
    Technique("screen_capture", None, ("screen",), False,
              "Real recorded software interaction (Playwright / LibreOffice recorders; not yet ported)"),
    Technique("character_animation", None, ("story", "explain"), False,
              "Rigged character performing actions (no free capability yet)"),
]}


class TechniqueError(ValueError):
    pass


def validate_params(name: str, params: dict[str, Any]) -> BaseModel:
    tech = REGISTRY.get(name)
    if tech is None:
        raise TechniqueError(f"unknown technique '{name}'")
    if not tech.available or tech.params is None:
        raise TechniqueError(f"technique '{name}' is not renderable yet ({tech.renders})")
    try:
        return tech.params(**params)
    except ValidationError as e:
        errs = "; ".join(f"{'.'.join(map(str, x['loc']))}: {x['msg']}" for x in e.errors()[:4])
        raise TechniqueError(f"bad params for {name}: {errs}") from None


def catalog_for_director() -> list[dict[str, Any]]:
    """Machine-readable menu the Director is constrained to (schemas included)."""
    return [{"technique": t.name, "available": t.available, "worlds": list(t.worlds), "renders": t.renders,
             "params_schema": t.params.model_json_schema() if t.params else None} for t in REGISTRY.values()]
