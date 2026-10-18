"""Optional local tool detection; never installs dependencies automatically."""
from __future__ import annotations
import importlib.util
import shutil

def engine_status() -> dict[str, dict]:
    return {
        "remotion": {"available": bool(shutil.which("npx")), "requires": "Node/npm + @remotion/cli; check commercial license"},
        "motion_canvas": {"available": bool(shutil.which("npm")), "requires": "Node/npm + @motion-canvas/core and @motion-canvas/2d"},
        "manim": {"available": importlib.util.find_spec("manim") is not None, "requires": "Python manim + rendering dependencies"},
        "logicscript": {"available": None, "requires": "Existing engine adapter audit"},
        "alan7": {"available": None, "requires": "Existing engine adapter audit"},
    }
