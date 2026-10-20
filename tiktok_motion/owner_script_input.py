"""User-authored scripts -> exact, reviewable motion storyboard.

Supports .txt/.md paragraphs (fast phone-friendly input) and structured .json
with one direction per scene. It does NOT rewrite narration, generate voice,
publish, call paid APIs, or pretend that freeform directions are already rendered.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path

KINDS = frozenset({"kinetic", "cards", "chart", "process", "ui", "timeline"})
W, H, FPS = 1080, 1920, 30


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be nonempty text")
    return value


def _estimated_seconds(narration: str) -> int:
    """Planning only: actual Chatterbox audio length must be measured later."""
    return max(5, math.ceil(len(narration.split()) * 60 / 135 + 1.5))


def build_from_owner_file(path: str | Path) -> dict:
    """Preserve the exact user-authored narration strings per scene."""
    path = Path(path)
    source_bytes = path.read_bytes()
    source = source_bytes.decode("utf-8-sig")
    if not source.strip():
        raise ValueError("Owner script cannot be blank")
    is_json = path.suffix.lower() == ".json"
    if is_json:
        data = json.loads(source)
        if not isinstance(data, dict):
            raise ValueError("JSON must contain an object")
        title = _text(data.get("title"), "title")
        language = data.get("language", "en")
        raw_scenes = data.get("scenes")
        if not isinstance(raw_scenes, list) or not raw_scenes:
            raise ValueError("At least one scene is required")
    else:
        lines = source.strip().splitlines()
        title = path.stem.replace("_", " ")
        if lines and lines[0].startswith("# "):
            title = lines.pop(0)[2:].strip()
        # Blank lines mark separate narration scenes; words are never rephrased.
        raw_scenes = [
            {"narration": paragraph.strip(), "kind": "kinetic"}
            for paragraph in re.split(r"\n\s*\n", "\n".join(lines))
            if paragraph.strip()
        ]
        language = "en"
    _text(title, "title")
    if language not in ("en", "es"):
        raise ValueError("language must be en or es")
    scenes = []
    warnings = []
    cursor = 0
    for index, scene in enumerate(raw_scenes, 1):
        if not isinstance(scene, dict):
            raise ValueError(f"Scene {index} must be an object")
        narration = _text(scene.get("narration"), f"scene {index} narration")
        kind = scene.get("kind", "kinetic")
        if kind not in KINDS:
            raise ValueError(f"Scene {index} unsupported visual kind {kind!r}")
        seconds = scene.get("duration_seconds", _estimated_seconds(narration))
        if isinstance(seconds, bool) or not isinstance(seconds, int) or not 3 <= seconds <= 90:
            raise ValueError(f"Scene {index} duration_seconds must be an integer from 3 to 90")
        on_screen = scene.get("on_screen", f"Scene {index}")
        if not isinstance(on_screen, str) or len(on_screen) > 110:
            raise ValueError(f"Scene {index} on_screen must be short text")
        items = scene.get("items", [])
        if (not isinstance(items, list) or len(items) > 6 or
                any(not isinstance(x, str) or not x.strip() or len(x) > 48 for x in items)):
            raise ValueError(f"Scene {index} items must contain up to six short labels")
        if kind in ("cards", "chart", "process", "timeline") and not items:
            raise ValueError(f"Scene {index} {kind} requires items")
        notes = scene.get("visual_notes", "")
        if not isinstance(notes, str):
            raise ValueError(f"Scene {index} visual_notes must be text")
        if notes.strip():
            warnings.append(
                f"Scene {index}: exact freeform visual_notes require human review; "
                "the template alone does not prove these directions were followed."
            )
        scenes.append({
            "start_seconds": cursor,
            "end_seconds": cursor + seconds,
            "kind": kind,
            "narration": narration,
            "on_screen_text": on_screen,
            "items": items,
            "visual_direction": notes,
        })
        cursor += seconds
    if cursor > 600:
        raise ValueError("Maximum duration is ten minutes")
    if not is_json:
        warnings.append("Plain text uses generic kinetic scenes. Use JSON for exact scene instructions.")
    return {
        "title": title, "language": language,
        "width": W, "height": H, "fps": FPS,
        "duration_seconds": cursor, "scenes": scenes,
        "source_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "owner_supplied_script": True,
        "narration_rewritten": False,
        "requires_owner_approval": True,
        "auto_publish": False,
        "premium_quality_owner_approved": False,
        "visual_direction_review_required": bool(
            any(s["visual_direction"].strip() for s in scenes)
        ),
        "warnings": warnings,
    }


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(
        description="Exact owner-written script -> scene directions, no publication"
    )
    parser.add_argument("--script", type=Path, required=True)
    parser.add_argument("--plan-out", type=Path, required=True)
    args = parser.parse_args(argv)
    plan = build_from_owner_file(args.script)
    args.plan_out.parent.mkdir(parents=True, exist_ok=True)
    args.plan_out.write_text(json.dumps(plan, indent=2, ensure_ascii=False)+"\n",
                             encoding="utf-8")
    print(json.dumps({
        "scenes": len(plan["scenes"]),
        "estimated_seconds": plan["duration_seconds"],
        "owner_approval_required": True,
        "warnings": plan["warnings"],
        "storyboard": str(args.plan_out),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
