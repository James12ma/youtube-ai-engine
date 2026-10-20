"""Deterministic, zero-cost storyboard contract for short vertical explainers.

This module prepares timed visual directions and narration; it does not publish.
Existing Alan7, LogicScript and publication gates remain untouched.
"""
from __future__ import annotations

import json
from pathlib import Path

WIDTH = 1080
HEIGHT = 1920
FPS = 30


def build_demo() -> dict:
    # Scenes: (start, end, kind, on_screen_text, visual_direction, narration)
    scenes_raw = [
        (
            0, 5, "hook",
            "NO INTERNET FOR 24 HOURS?",
            "Bold kinetic type; disconnect icon pulsing",
            "What if the internet disappeared for twenty-four hours?",
        ),
        (
            5, 15, "map",
            "A world suddenly offline",
            "Animated vector world map; network links fade out",
            "Across the planet, connections would drop. Maps go dark. The global network vanishes in minutes.",
        ),
        (
            15, 25, "devices",
            "Messages and online payments stall",
            "Phone and payment terminal motion graphics; red X overlays",
            "Messages freeze. Online payments stall. Phones become expensive clocks.",
        ),
        (
            25, 40, "systems",
            "Businesses scramble for offline alternatives",
            "Store, logistics and service icons; moving counters and queues",
            "Stores scramble. Logistics reroute. Banks fall back to paper and local systems. Cities adapt under pressure.",
        ),
        (
            40, 52, "nuance",
            "Not everything would stop",
            "Offline-capable tools and local networks highlighted in accent color",
            "But not everything stops. Radio, cash, and local networks keep working. Communities reconnect the old way.",
        ),
        (
            52, 60, "outro",
            "What would YOU do first?",
            "High contrast question and subtle follow prompt",
            "So what would you do first? This is a hypothetical scenario, not real news.",
        ),
    ]
    result = {
        "id": "tiktok-demo-001",
        "title": "What If the Internet Disappeared for 24 Hours?",
        "language": "en",
        "content_type": "hypothetical_explainer",
        "disclaimer": "A hypothetical scenario, not a report of a real outage.",
        "width": WIDTH,
        "height": HEIGHT,
        "fps": FPS,
        "duration_seconds": 60,
        "palette": {
            "background": "#FAF9F6",
            "ink": "#151515",
            "accent": "#E63336",
            "muted": "#BBBBBB",
        },
        "requires_owner_approval": True,
        "auto_publish": False,
        "scenes": [
            {
                "start_seconds": start,
                "end_seconds": end,
                "kind": kind,
                "on_screen_text": text,
                "visual_direction": visual,
                "narration": narration,
            }
            for start, end, kind, text, visual, narration in scenes_raw
        ],
    }
    validate_storyboard(result)
    return result


def full_narration_text(data: dict | None = None) -> str:
    data = data or build_demo()
    return " ".join(s["narration"] for s in data["scenes"])


def validate_storyboard(data: dict) -> None:
    if (data["width"], data["height"], data["fps"]) != (WIDTH, HEIGHT, FPS):
        raise ValueError("Invalid vertical video dimensions or frame rate")
    if data.get("auto_publish") is not False or data.get("requires_owner_approval") is not True:
        raise ValueError("Owner approval is mandatory")
    cursor = 0
    for scene in data["scenes"]:
        if scene["start_seconds"] != cursor or scene["end_seconds"] <= cursor:
            raise ValueError("Scenes must form a continuous, positive timeline")
        if not scene.get("narration"):
            raise ValueError("Every scene requires English narration text")
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
    print(full_narration_text())
