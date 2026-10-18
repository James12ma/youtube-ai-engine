"""Deterministic scene-to-engine routing. No external calls or publishing."""
from __future__ import annotations

ENGINES = ("remotion", "motion_canvas", "manim", "logicscript", "alan7")

def choose_engine(kind: str, mode: str = "tiktok") -> str:
    if mode == "screen_tutorial":
        return "logicscript"
    if mode == "documentary":
        return "alan7"
    if kind in {"chart", "math", "equation", "statistics"}:
        return "manim"
    if kind in {"map", "diagram", "network", "flow"}:
        return "motion_canvas"
    return "remotion"

def route_storyboard(storyboard: dict, mode: str = "tiktok") -> list[dict]:
    return [{**scene, "engine": choose_engine(scene["kind"], mode)} for scene in storyboard["scenes"]]
