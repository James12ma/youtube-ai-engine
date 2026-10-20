"""Engine adapters. Real Manim path; honest status for Node engines."""
from __future__ import annotations

import importlib.util
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any


def available_engines() -> dict[str, dict[str, Any]]:
    manim_ok = importlib.util.find_spec("manim") is not None
    npx = shutil.which("npx")
    remotion_pkg = Path("node_modules/remotion").exists() or Path("tiktok_motion/node_engines/remotion/node_modules/remotion").exists()
    mc_pkg = Path("node_modules/@motion-canvas/core").exists()
    return {
        "manim": {
            "available": manim_ok,
            "license": "MIT (Manim Community)",
            "notes": "Fully wired; renders vertical 1080x1920 MP4",
        },
        "remotion": {
            "available": bool(npx and remotion_pkg),
            "license": "Remotion Free License (individuals / orgs ≤3 employees); Company License required for larger orgs. Source-available, not OSI OSS.",
            "notes": "Adapter scaffold present. Blocked in this environment by npm registry 502 errors during package install.",
        },
        "motion_canvas": {
            "available": bool(npx and mc_pkg),
            "license": "MIT",
            "notes": "Adapter scaffold present. Blocked in this environment by npm registry 502 errors during package install.",
        },
        "pillow": {
            "available": True,
            "license": "PIL/Pillow (HPND)",
            "notes": "Fallback / composition engine always available",
        },
    }


def render_manim_scene(scene_module: Path, scene_class: str, output: Path, quality: str = "h") -> Path:
    """Render a Manim Community scene to MP4."""
    if not importlib.util.find_spec("manim"):
        raise RuntimeError("manim not installed")
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    media = Path(tempfile.mkdtemp(prefix="manim-out-"))
    cmd = [
        "manim", f"-q{quality}", "--format=mp4",
        f"--media_dir={media}",
        str(scene_module), scene_class,
    ]
    subprocess.run(cmd, check=True)
    found = list(media.rglob(f"{scene_class}.mp4"))
    if not found:
        raise RuntimeError(f"Manim did not produce {scene_class}.mp4")
    shutil.copyfile(found[0], output)
    return output


def render_scene(engine: str, scene_spec: dict, output: Path) -> Path:
    """Dispatch to the requested engine. Raises if unavailable."""
    status = available_engines()
    if engine not in status:
        raise ValueError(f"Unknown engine: {engine}")
    if not status[engine]["available"]:
        raise RuntimeError(
            f"Engine '{engine}' not available: {status[engine].get('notes')}"
        )
    if engine == "manim":
        mod = Path(scene_spec["module"])
        return render_manim_scene(mod, scene_spec["class"], output)
    if engine == "pillow":
        from tiktok_motion.render import render as pillow_render
        return pillow_render(output, voice=scene_spec.get("voice"))
    raise RuntimeError(f"No renderer implementation for {engine}")
