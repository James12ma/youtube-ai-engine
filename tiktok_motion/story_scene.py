"""Validated, script-bound visual scene grammar for the existing premium renderer.

No LLM calls, asset downloads, invented measurements, publishing or fallback renders.
A structured owner script supplies explicit concrete actions and references.
"""
from __future__ import annotations

import math

LEGACY_KINDS = frozenset({"kinetic", "cards", "process", "ui", "timeline", "chart"})
STORY_KINDS = frozenset({"character", "device", "signal_flow", "document", "data", "map", "hero", "god_eye"})
ALL_KINDS = LEGACY_KINDS | STORY_KINDS
CAMERAS = frozenset({"static", "push_in", "pan_left", "pan_right", "orbit"})


def _short_text(value, label, limit):
    if not isinstance(value, str) or len(value) > limit:
        raise ValueError(f"Invalid {label}")
    return value.strip()


def enrich_visual(scene):
    """Validate scene-specific visual details without modifying narration."""
    if not isinstance(scene, dict):
        raise ValueError("Scene must be an object")
    kind = scene.get("kind", "kinetic")
    if kind not in ALL_KINDS:
        raise ValueError("Unsupported scene kind")
    actors = scene.get("actors", [])
    if not isinstance(actors, list) or len(actors) > 3:
        raise ValueError("Invalid scene actors")
    actors = [_short_text(a, "actor", 36) for a in actors]
    if any(not a for a in actors) or len(set(actors)) != len(actors):
        raise ValueError("Invalid scene actors")
    if kind == "character" and not actors:
        raise ValueError("Character scene requires at least one named role")
    camera = scene.get("camera", "push_in")
    if camera not in CAMERAS:
        raise ValueError("Unsupported camera motion")
    flow = scene.get("flow", {})
    if not isinstance(flow, dict) or set(flow) - {"from", "to"}:
        raise ValueError("Invalid flow endpoints")
    flow = {k: _short_text(v, k, 48) for k, v in flow.items()}
    if kind == "signal_flow" and (not flow.get("from") or not flow.get("to")):
        raise ValueError("Signal flow requires explicit from and to")
    data = scene.get("data", [])
    if not isinstance(data, list) or len(data) > 6:
        raise ValueError("Invalid numeric data")
    points = []
    for point in data:
        if not isinstance(point, dict) or set(point) != {"label", "value"}:
            raise ValueError("Numeric point requires label and value")
        label = _short_text(point["label"], "data label", 32)
        value = point["value"]
        if not label or isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            raise ValueError("Invalid numeric point")
        points.append({"label": label, "value": value})
    if kind == "data" and not points:
        raise ValueError("Data scene requires supplied numeric measurements")
    # God's Eye View is an explicit, locally-rendered and reviewed video asset.
    # Never fetch third-party tiles or launch paid providers from this validator.
    geo_clip = scene.get("geo_clip", "")
    geo_attribution = _short_text(scene.get("geo_attribution", ""), "geographic attribution", 160)
    if kind == "god_eye":
        import re
        if not isinstance(geo_clip, str) or not re.fullmatch(
            r"job/god_eye_[a-zA-Z0-9_-]{1,64}\.mp4", geo_clip
        ):
            raise ValueError("God's Eye View scene requires a reviewed local job/god_eye_*.mp4 clip")
        if not geo_attribution:
            raise ValueError("God's Eye View scene requires source attribution and imagery license review")
        if not any(word in scene.get("narration", "").lower() for word in (
            "world", "global", "country", "countries", "region", "ocean",
            "earth", "geograph", "continent", "migration", "route", "map",
        )):
            raise ValueError("God's Eye View is only for geographically meaningful narration")
    elif geo_clip:
        raise ValueError("Only a god_eye scene may contain a geographic video clip")
    excerpt = _short_text(scene.get("excerpt", ""), "document excerpt", 180)
    if kind == "document" and not excerpt:
        raise ValueError("Document scene requires a supplied excerpt")
    return {
        "actors": actors,
        "setting": _short_text(scene.get("setting", ""), "setting", 80),
        "action": _short_text(scene.get("action", ""), "action", 180),
        "camera": camera,
        "flow": flow,
        "data": points,
        "excerpt": excerpt,
        "source_label": _short_text(scene.get("source_label", ""), "source label", 100),
        "geo_clip": geo_clip,
        "geo_attribution": geo_attribution,
    }
