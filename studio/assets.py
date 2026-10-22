"""Turn a spec's AssetRequests into a WanGP GPU job, and file the generated media back into the film.

Model choices are the ones proven on the GPU probe; change MODELS after a new probe, not per film.
Character consistency: an entity's appearance text and seed go into every prompt that features it.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from .spec import FilmSpec

WANGP_COMMIT = "9d25c60"
MODELS = {
    "image": {"model_type": "z_image_twinflow_turbo"},
    "video": {"model_type": "i2v_2_2_Enhanced_Lightning_v2", "image_prompt_type": "S"},
    "music": {"model_type": "ace_step_v1_5_turbo_lm_1_7b"},
}
STYLE_SUFFIX = {
    "editorial_two_world": "Photorealistic, cinematic color grading, natural imperfections, no text, no watermark, no logos.",
    "documentary": "Photorealistic documentary photograph, natural light, no text, no watermark.",
}


def _size(spec: FilmSpec, kind: str) -> str:
    vertical = spec.format.height >= spec.format.width
    if kind == "image":
        return "768x1344" if vertical else "1344x768"
    return "480x832" if vertical else "832x480"


def gpu_request(spec: FilmSpec, only: set[str] | None = None) -> dict:
    tasks = []
    suffix = STYLE_SUFFIX.get(spec.style, STYLE_SUFFIX["editorial_two_world"])
    order = sorted(spec.assets.items(), key=lambda kv: kv[1].kind != "image")  # stills before the clips that use them
    for aid, req in order:
        if only and aid not in only:
            continue
        looks = "; ".join(f"{spec.entities[e].name}: {spec.entities[e].appearance}" for e in req.entities
                          if spec.entities[e].appearance)
        seed = next((spec.entities[e].seed for e in req.entities if spec.entities[e].seed is not None), 1234)
        settings = {**MODELS[req.kind], "prompt": " ".join(x for x in (req.prompt, looks and f"({looks})", suffix) if x),
                    "seed": seed}
        if req.kind in ("image", "video"):
            settings["resolution"] = _size(spec, req.kind)
        if req.kind == "video":
            settings["video_length"] = int(round(req.seconds * 16)) // 4 * 4 + 1  # Wan 2.2: 16 fps, 4n+1 frames
            if req.source_image:
                settings["image_start"] = f"@{req.source_image}"
        if req.kind == "music":
            settings["duration_seconds"] = req.seconds
        tasks.append({"id": aid, "settings": settings})
    return {"purpose": f"assets for film {spec.id}", "wangp_commit": WANGP_COMMIT,
            "cli_args": ["--attention", "sdpa", "--profile", "4"], "max_seconds": 15000, "tasks": tasks}


def file_outputs(gpu_out: Path, film: Path) -> list[str]:
    """Copy `<asset id>_0.<ext>` files produced by studio/gpu/wangp_job.py into film/assets/<asset id>.<ext>."""
    (film / "assets").mkdir(parents=True, exist_ok=True)
    done = []
    for p in sorted(gpu_out.glob("*_0.*")):
        aid = p.stem[:-2]
        shutil.copyfile(p, film / "assets" / f"{aid}{p.suffix}")
        done.append(aid)
    return done


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Write the GPU request for a film's assets")
    ap.add_argument("film", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    spec = FilmSpec(**json.loads((a.film / "spec.json").read_text()))
    a.out.write_text(json.dumps(gpu_request(spec), indent=1) + "\n")
    print(a.out)
