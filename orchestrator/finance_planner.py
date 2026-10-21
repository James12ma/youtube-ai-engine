"""Finance visual planner for the existing premium Remotion pipeline.

Owner narration remains word-for-word unchanged. This module only segments it and
chooses visuals. A scene plan with unsupported or unsourced numbers fails closed.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator
from adapters.base import LLMRequest
from router.router import Router

SceneKind = Literal["hero", "data", "document", "map"]
GEO = ("global", "worldwide", "international", "world", "country",
       "countries", "geography", "across borders")


class ChartPoint(BaseModel):
    label: str = Field(min_length=1, max_length=32)
    value: float = Field(ge=0, le=1e9)

    @field_validator("value")
    @classmethod
    def finite(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("chart value must be finite")
        return value


class FinanceScene(BaseModel):
    narration: str = Field(min_length=10, max_length=3000)
    kind: SceneKind
    on_screen: str = Field(min_length=3, max_length=110)
    items: list[str] = Field(default_factory=list, max_length=6)
    data: list[ChartPoint] = Field(default_factory=list, max_length=6)
    excerpt: str = Field(default="", max_length=180)
    source_label: str = Field(default="", max_length=100)
    camera: Literal["static", "push_in", "pan_left", "pan_right", "orbit"] = "push_in"
    facts: list[str] = Field(default_factory=list)

    @field_validator("items")
    @classmethod
    def short_items(cls, values: list[str]) -> list[str]:
        if any(len(value) > 60 for value in values):
            raise ValueError("item exceeds 60 characters")
        return values

    @model_validator(mode="after")
    def semantics(self):
        if self.kind == "data":
            if not self.data:
                raise ValueError("data scene needs actual numeric points")
            # No made-up 'source:' URLs may be treated as verification.
            # MVP uses explicitly labeled hypothetical examples only.
            if not self.facts or not all(f.startswith("ILLUSTRATIVE:") for f in self.facts):
                raise ValueError("data needs ILLUSTRATIVE: labels; sourced claims need independent verification")
            if "illustrative" not in self.on_screen.lower():
                raise ValueError("illustrative data must be labeled visibly on screen")
        if self.kind == "document":
            if not self.excerpt or not self.source_label:
                raise ValueError("document requires excerpt and attribution")
            # Do not portray invented quotations as authentic documents.
            if self.source_label != "Illustrative example":
                raise ValueError("unverified document excerpt must say Illustrative example")
        if self.kind == "map" and not any(w in self.narration.lower() for w in GEO):
            raise ValueError("map must express a geographic part of the narration")
        return self


class FinancePlan(BaseModel):
    title: str = Field(min_length=3, max_length=100)
    scenes: list[FinanceScene] = Field(min_length=6, max_length=10)

    @model_validator(mode="after")
    def shape(self):
        kinds = [scene.kind for scene in self.scenes]
        if kinds[0] not in ("hero", "data"):
            raise ValueError("first scene must be hero or data")
        if "data" not in kinds or len(set(kinds)) < 3:
            raise ValueError("need data and at least three meaningful visual types")
        if kinds.count("hero") > 2:
            raise ValueError("maximum two hero scenes")
        return self


SYSTEM = """Return JSON matching FinancePlan schema.
You are assigning visuals to an existing owner-supplied English narration.
DO NOT add, delete, paraphrase or reorder ANY spoken words. Split original script
into six to ten contiguous scenes; joining scene narration with spaces must
equal the original script after whitespace normalization.
Each shot must demonstrate what its narration says, not add decoration.
Allowed kinds: hero (hook/key idea), data (bar chart), document
(illustrative text snippet), map (only if narration references geography).
Data values are purely hypothetical; every 'facts' entry starts 'ILLUSTRATIVE:',
and the on_screen headline MUST visibly contain 'Illustrative'.
Never claim hypothetical data is historical CPI or sourced statistics.
Document scenes: source_label must be 'Illustrative example' and not a fabricated
quotation attributed to a real organization. Map needs a geographic sentence.
Avoid forcing meaningless scene styles; reject unsupported planning.
Output a single JSON object, no commentary."""


def _words(text: str) -> str:
    return " ".join(text.split())


def plan(script_text: str, router: Router) -> FinancePlan:
    if not isinstance(script_text, str) or len(script_text.split()) < 20 or len(script_text) > 12000:
        raise ValueError("Finance mode requires an English owner script, 20+ words, up to 12000 chars")
    digest = hashlib.sha256(script_text.encode("utf-8")).hexdigest()
    request = LLMRequest(
        messages=[{"role": "system", "content": SYSTEM},
                  {"role": "user", "content": script_text}],
        schema=FinancePlan,
        temperature=0.2,
        max_tokens=4096,
        metadata={"pipeline": "finance_visual_plan", "script_sha256": digest},
    )
    result = router.execute("finance_visual_plan", {"sha256": digest}, request, FinancePlan)
    if _words(" ".join(scene.narration for scene in result.scenes)) != _words(script_text):
        raise ValueError("Finance planner changed owner narration; refused")
    return result


def to_premium_script(value: FinancePlan) -> str:
    return json.dumps({"title": value.title, "scenes": [
        {"narration": s.narration, "kind": s.kind,
         "on_screen": s.on_screen, "items": s.items,
         "camera": s.camera,
         "data": [p.model_dump() for p in s.data],
         "excerpt": s.excerpt, "source_label": s.source_label,
         "visual_notes": "Illustrative values only — owner review required" if s.kind == "data" else ""}
        for s in value.scenes]}, ensure_ascii=False)
