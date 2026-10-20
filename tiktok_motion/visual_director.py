"""Deterministic scene-to-engine routing. No external calls or publishing."""
from __future__ import annotations

from .engines.adapters import available_engines

ENGINES = ("remotion", "motion_canvas", "manim", "pillow", "logicscript", "alan7")


def choose_engine(kind: str, mode: str = "tiktok") -> str:
    """Pick best available engine for a scene kind."""
    if mode == "screen_tutorial":
        return "logicscript"
    if mode == "documentary":
        return "alan7"
    status = available_engines()
    preferred = {
        "chart": "manim",
        "math": "manim",
        "equation": "manim",
        "statistics": "manim",
        "systems": "manim",
        "map": "motion_canvas",
        "diagram": "motion_canvas",
        "network": "motion_canvas",
        "flow": "motion_canvas",
        "hook": "remotion",
        "outro": "remotion",
        "devices": "remotion",
        "nuance": "remotion",
    }.get(kind, "remotion")
    if status.get(preferred, {}).get("available"):
        return preferred
    # Fallbacks
    if status.get("manim", {}).get("available") and kind in {
        "chart", "math", "equation", "statistics", "systems"
    }:
        return "manim"
    return "pillow"


def route_storyboard(storyboard: dict, mode: str = "tiktok") -> list[dict]:
    return [
        {**scene, "engine": choose_engine(scene["kind"], mode)}
        for scene in storyboard["scenes"]
    ]
