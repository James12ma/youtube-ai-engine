"""Configuration du moteur d'animation (valeurs par défaut + chargement d'un job JSON)."""
import json
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DEFAULTS = {
    "fps": 24,
    "seconds": 5,
    "render": {
        "engine": "CYCLES",          # seul moteur fiable en headless sans GPU/OpenGL
        "device": "CPU",
        "width": 540,                # rendu natif, puis mise à l'échelle 1080x1920 par FFmpeg
        "height": 960,
        "samples": 10,
        "denoise": True,
        "final_width": 1080,
        "final_height": 1920,
        "crf": 20,
    },
    # Géométrie en mètres (échelle « cartoon »)
    "counter_top_z": 0.90,
    "mug": {"x": 0.15, "y": 0.30, "radius": 0.050, "height": 0.12},
    "pot": {"x": -0.24, "y": 0.42},
    "hand_radius": 0.045,
    "fig_a": {"name": "FigA", "x": 0.36, "y": 0.85, "shirt": [0.12, 0.30, 0.18], "skin": [0.36, 0.22, 0.14]},
    "fig_b": {"name": "FigB", "x": -0.36, "y": 0.85, "shirt": [0.80, 0.50, 0.55], "skin": [0.50, 0.32, 0.22]},
    # Chronologie (images)
    "timeline": {
        "reach_start": 20, "pre_contact": 45, "contact": 50, "push_end": 75,
        "retract_end": 100,
        "head_turn_start": 70, "head_turn_end": 85,
        "react_start": 82, "react_peak": 92,
    },
    "push_distance": 0.30,           # distance de poussée demandée à la cible IK
    "head_turn_deg": 35.0,
}


def deep_merge(base, over):
    out = deepcopy(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load(job_path=None):
    if not job_path:
        return deepcopy(DEFAULTS)
    job = json.loads(Path(job_path).read_text(encoding="utf-8"))
    return deep_merge(DEFAULTS, job.get("config", {}))
