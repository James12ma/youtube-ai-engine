"""Render a film: spec + assets folder -> plan -> Remotion editor -> MP4 (+ stills for review).

    python -m studio.render studio/films/gate_a --preview            # estimated timing, pending assets allowed
    python -m studio.render studio/films/gate_a --out out/film.mp4   # final: needs voice word times + all assets
    python -m studio.render studio/films/gate_a --preview --stills 30,200,400

A film folder holds spec.json, optional voice.json ({"audio": "voice.wav", "word_times": [[s, e], ...]}),
and assets/ (files named after asset ids, any extension). Assets are copied into the editor's public/.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path

from .audio.sfx import write_all as write_sfx
from .spec import FilmSpec
from .timeline import build_plan

EDITOR = Path(__file__).resolve().parent / "editor"
MEDIA_EXT = {".png", ".jpg", ".jpeg", ".webp", ".mp4", ".webm", ".mov", ".wav", ".mp3", ".m4a"}


def chrome_args() -> list[str]:
    exe = os.environ.get("REMOTION_CHROME") or next(
        (str(p) for p in Path("/opt/pw-browsers").glob("chromium_headless_shell-*/chrome-linux/headless_shell")), "")
    return [f"--browser-executable={exe}"] if exe else []


def stage(film: Path, preview: bool) -> dict:
    spec = FilmSpec(**json.loads((film / "spec.json").read_text()))
    public = EDITOR / "public"
    (public / "assets").mkdir(parents=True, exist_ok=True)
    assets: dict[str, str] = {}
    for p in sorted((film / "assets").glob("*")) if (film / "assets").exists() else []:
        if p.suffix.lower() in MEDIA_EXT:
            dst = public / "assets" / p.name
            if not dst.exists() or dst.stat().st_mtime < p.stat().st_mtime:
                shutil.copyfile(p, dst)
            assets[p.stem] = f"assets/{p.name}"
    voice = film / "voice.json"
    if voice.exists():
        v = json.loads(voice.read_text())
        spec.narration.word_times = [tuple(x) for x in v["word_times"]]
        spec.narration.audio = Path(v["audio"]).stem
    if not (public / "sfx" / "tap.wav").exists():
        write_sfx(public / "sfx")
    plan = build_plan(spec, assets=assets, preview=preview)
    if not preview and plan["missing_assets"]:
        raise SystemExit(f"missing assets for final render: {plan['missing_assets']}")
    (public / "plan.json").write_text(json.dumps(plan, indent=1))
    return plan


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("film", type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--stills", default="")
    ap.add_argument("--scale", type=float, default=1.0)
    a = ap.parse_args()
    plan = stage(a.film, a.preview)
    print(json.dumps({k: plan[k] for k in ("id", "durationInFrames", "missing_assets", "warnings", "preview_timing")}))
    base = ["npx", "remotion"]
    common = ["src/index.ts", "Film", f"--props={json.dumps({'planFile': 'plan.json'})}", "--log=error", *chrome_args()]
    if a.scale != 1.0:
        common.append(f"--scale={a.scale}")
    for fr in [int(x) for x in a.stills.split(",") if x]:
        out = (a.out.parent if a.out else a.film / "out") / f"still_{fr:04d}.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([*base, "still", *common[:2], str(out.resolve()), *common[2:], f"--frame={fr}"], cwd=EDITOR, check=True)
        print(out)
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([*base, "render", *common[:2], str(a.out.resolve()), *common[2:]], cwd=EDITOR, check=True)
        print(a.out)


if __name__ == "__main__":
    main()
