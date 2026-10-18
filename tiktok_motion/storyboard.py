"""Deterministic, zero-cost storyboard contract for short vertical explainers.

This module prepares timed visual directions; it does not claim to render MP4s.
Existing Alan7, LogicScript and publication gates remain untouched.
"""
from __future__ import annotations

import json
from pathlib import Path

WIDTH = 1080
HEIGHT = 1920
FPS = 30


def build_demo() -> dict:
    scenes = [
        (0, 5, "hook", "NO INTERNET FOR 24 HOURS?", "Bold kinetic type; disconnect icon"),
        (5, 15, "map", "A world suddenly offline", "Animated vector map; network links fade"),
        (15, 25, "devices", "Messages and online payments stall", "Phone and payment terminal motion graphics"),
        (25, 40, "systems", "Businesses scramble for offline alternatives", "Store, logistics and service icons; moving counters"),
        (40, 52, "nuance", "Not everything would stop", "Offline-capable tools and local networks highlighted"),
        (52, 60, "outro", "What would YOU do first?", "High contrast question and subtle follow prompt"),
    ]
    result = {
        "id": "tiktok-demo-001",
        "title": "What If the Internet Disappeared for 24 Hours?",
        "language": "en",
        "content_type": "hypothetical_explainer",
        "disclaimer": "A hypothetical scenario, not a report of a real outage.",
        "width": WIDTH, "height": HEIGHT, "fps": FPS,
        "duration_seconds": 60,
        "palette": {"background": "#FAF9F6", "ink": "#151515", "accent": "#E63336"},
        "requires_owner_approval": True,
        "auto_publish": False,
        "scenes": [
            {"start_seconds": start, "end_seconds": end, "kind": kind,
             "on_screen_text": text, "visual_direction": visual}
            for start, end, kind, text, visual in scenes
        ],
    }
    validate_storyboard(result)
    return result


def validate_storyboard(data: dict) -> None:
    if (data["width"], data["height"], data["fps"]) != (WIDTH, HEIGHT, FPS):
        raise ValueError("Invalid vertical video dimensions or frame rate")
    if data.get("auto_publish") is not False or data.get("requires_owner_approval") is not True:
        raise ValueError("Owner approval is mandatory")
    cursor = 0
    for scene in data["scenes"]:
        if scene["start_seconds"] != cursor or scene["end_seconds"] <= cursor:
            raise ValueError("Scenes must form a continuous, positive timeline")
        cursor = scene["end_seconds"]
    if cursor != data["duration_seconds"]:
        raise ValueError("Timeline duration mismatch")


def write_demo(path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(build_demo(), indent=2) + "\n", encoding="utf-8")
    return target


if __name__ == "__main__":
    write_demo("tiktok_motion/demo_storyboard.json")
