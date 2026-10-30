"""Pipeline headless : build -> render -> encode -> qa, avec état de job persistant et reprise.

Usage : python -m engine.run jobs/poc-001.json [--stage all|build|render|encode|qa] [--frames 1,60,120]
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

from . import config
from .jobs import Job

ROOT = config.ROOT


def out_dir(job):
    d = ROOT / "output" / job.id
    (d / "frames").mkdir(parents=True, exist_ok=True)
    return d


def stage_build(job, cfg):
    import bpy
    from . import scene
    job.set("building")
    t0 = time.time()
    res = scene.build(cfg)
    d = out_dir(job)
    scene.export_state(cfg, res["a"], res["b"], res["mug"], res["pot"], d / "state.json")
    bpy.ops.wm.save_as_mainfile(filepath=str(d / "scene.blend"))
    job.update(contact_frames=res["contact_frames"], build_seconds=round(time.time() - t0, 1))
    return res


def configure_render(cfg):
    import bpy
    r, sc = cfg["render"], bpy.context.scene
    sc.render.engine = r["engine"]
    sc.cycles.device = r["device"]
    sc.cycles.samples = r["samples"]
    sc.cycles.use_denoising = r["denoise"]
    sc.cycles.use_adaptive_sampling = True
    sc.render.resolution_x, sc.render.resolution_y = r["width"], r["height"]
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"
    sc.render.use_persistent_data = True


def stage_render(job, cfg, only=None):
    import bpy
    d = out_dir(job)
    blend = d / "scene.blend"
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    configure_render(cfg)
    job.set("rendering")
    frames = only or range(1, cfg["fps"] * cfg["seconds"] + 1)
    times = []
    for f in frames:
        target = d / "frames" / f"frame_{f:04d}.png"
        if target.exists() and target.stat().st_size > 0:
            continue  # reprise : image déjà rendue
        t0 = time.time()
        bpy.context.scene.frame_set(f)
        bpy.context.scene.render.filepath = str(target)
        bpy.ops.render.render(write_still=True)
        times.append(time.time() - t0)
        print(f"frame {f} {times[-1]:.1f}s", flush=True)
    if times:
        job.update(sec_per_frame=round(sum(times) / len(times), 2))


def stage_encode(job, cfg):
    d, r = out_dir(job), cfg["render"]
    job.set("encoding")
    mp4 = d / f"{job.id}.mp4"
    cmd = ["ffmpeg", "-y", "-v", "error", "-framerate", str(cfg["fps"]),
           "-i", str(d / "frames" / "frame_%04d.png"),
           "-vf", f"scale={r['final_width']}:{r['final_height']}:flags=lanczos,format=yuv420p",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", str(r["crf"]), "-movflags", "+faststart", str(mp4)]
    subprocess.run(cmd, check=True)
    job.update(output=str(mp4.relative_to(ROOT)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("job")
    ap.add_argument("--stage", default="all")
    ap.add_argument("--frames", default=None, help="liste d'images, ex. 1,60,120 (rendu partiel)")
    a = ap.parse_args()
    job = Job(a.job)
    cfg = config.load(a.job)
    cfg["frames"] = cfg["fps"] * cfg["seconds"]
    only = [int(x) for x in a.frames.split(",")] if a.frames else None
    try:
        if a.stage in ("all", "build"):
            stage_build(job, cfg)
        if a.stage in ("all", "render"):
            stage_render(job, cfg, only)
        if a.stage in ("all", "encode"):
            stage_encode(job, cfg)
        if a.stage in ("all", "qa"):
            job.set("qa")
            from tests import qa
            ok = qa.run(job.id)
            job.set("done" if ok else "failed", reason=None if ok else "QA critique en échec")
            sys.exit(0 if ok else 1)
    except Exception as e:  # état d'échec persistant avec la cause
        job.set("failed", reason=f"{type(e).__name__}: {e}")
        raise


if __name__ == "__main__":
    main()
