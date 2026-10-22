"""Run a batch of WanGP generation tasks on a GPU host (Kaggle free GPU, or the owner's own PC).

Kaggle script kernels upload only one file, so the dispatcher prepends `REQUEST_JSON = '...'`
to this file. Locally: `python wangp_job.py request.json --root /path/to/Wan2GP --out out/`.

Request format:
    {"wangp_commit": "<sha>", "cli_args": ["--attention", "sdpa", "--profile", "4"],
     "max_seconds": 12000,
     "tasks": [{"id": "s01_img", "settings": {"model_type": "z_image_twinflow_turbo", "prompt": "...",
                "resolution": "768x1344", "seed": 7}},
               {"id": "s01_vid", "settings": {"model_type": "i2v_2_2_Enhanced_Lightning_v2", "prompt": "...",
                "image_start": "@s01_img", "image_prompt_type": "S", "resolution": "480x832",
                "video_length": 81}}]}

`"@<task id>"` in any string setting is replaced by the first file that task produced, so one
request can chain still -> image-to-video. Every task records duration, peak VRAM and its error;
one failed task never stops the rest. WanGP is used under the WanGP Community License.
"""

import json
import os
import shutil
import subprocess
import sys
import threading
import time
import traceback
from pathlib import Path

T0 = time.time()
WANGP_REPO = "https://github.com/deepbeepmeep/Wan2GP.git"


def sh(cmd: str, log: list, check: bool = False) -> int:
    p = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    log.append({"cmd": cmd, "rc": p.returncode, "tail": (p.stdout + p.stderr)[-1500:]})
    if check and p.returncode:
        raise RuntimeError(f"{cmd} -> {p.returncode}")
    return p.returncode


def environment(log: list) -> dict:
    env = {"python": sys.version.split()[0]}
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total,driver_version",
                              "--format=csv,noheader"], capture_output=True, text=True).stdout.strip()
        env["gpus"] = out.splitlines()
    except FileNotFoundError:
        env["gpus"] = []
    try:
        import torch
        env["torch"] = torch.__version__
        env["cuda"] = torch.version.cuda
        env["cuda_available"] = torch.cuda.is_available()
        if torch.cuda.is_available():
            env["capability"] = ".".join(map(str, torch.cuda.get_device_capability(0)))
    except Exception as e:  # noqa: BLE001 - reported, not raised
        env["torch_error"] = repr(e)
    env["disk_free_gb"] = round(shutil.disk_usage("/tmp").free / 1e9, 1)
    log.append({"environment": env})
    return env


def install(root: Path, commit: str, log: list) -> None:
    if not (root / "wgp.py").exists():
        sh(f"git clone -q --filter=blob:none {WANGP_REPO} {root}", log, check=True)
    if commit:
        sh(f"git -C {root} checkout -q {commit}", log, check=True)
    req = root / "requirements.txt"
    if sh(f"{sys.executable} -m pip install -q -r {req}", log):
        # Fall back to line-by-line so one unavailable optional wheel does not block the rest.
        for line in req.read_text().splitlines():
            line = line.split("#")[0].strip()
            if line and not line.startswith("-"):
                sh(f"{sys.executable} -m pip install -q '{line}'", log)


def resolve_refs(settings: dict, produced: dict) -> dict:
    out = {}
    for k, v in settings.items():
        if isinstance(v, str) and v.startswith("@"):
            files = produced.get(v[1:])
            if not files:
                raise ValueError(f"{k} references task {v[1:]} which produced nothing")
            v = files[0]
        out[k] = v
    return out


def run(request: dict, root: Path, out: Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    report: dict = {"request_tasks": [t["id"] for t in request["tasks"]], "setup": [], "tasks": []}

    def save():
        report["elapsed_s"] = round(time.time() - T0, 1)
        (out / "report.json").write_text(json.dumps(report, indent=1))

    def watchdog():
        report["error"] = f"watchdog: hard limit {request.get('max_seconds', 12000)} s reached"
        save()
        os._exit(3)

    threading.Timer(request.get("max_seconds", 12000), watchdog).start()
    report["env"] = environment(report["setup"])
    save()
    try:
        install(root, request.get("wangp_commit", ""), report["setup"])
        sys.path.insert(0, str(root))
        os.chdir(root)
        from shared.api import init  # noqa: PLC0415 - WanGP is only importable after install

        t = time.time()
        session = init(root=root, output_dir=out / "raw", cli_args=request.get("cli_args", []),
                       console_output=False)
        report["init_s"] = round(time.time() - t, 1)
    except Exception:  # noqa: BLE001
        report["error"] = "setup failed: " + traceback.format_exc()[-3000:]
        save()
        return report
    save()

    import torch

    produced: dict[str, list[str]] = {}
    for task in request["tasks"]:
        rec = {"id": task["id"], "model_type": task["settings"].get("model_type")}
        t = time.time()
        try:
            torch.cuda.reset_peak_memory_stats()
            settings = {**session.get_default_settings(task["settings"]["model_type"]),
                        **resolve_refs(task["settings"], produced)}
            result = session.submit_task(settings).result()
            rec["success"] = bool(result.success)
            rec["errors"] = [getattr(e, "message", str(e))[-800:] for e in (result.errors or [])]
            files = []
            for i, f in enumerate(result.generated_files or []):
                dst = out / f"{task['id']}_{i}{Path(f).suffix}"
                shutil.copyfile(f, dst)
                files.append(str(dst))
            produced[task["id"]] = files
            rec["files"] = [Path(f).name for f in files]
        except Exception:  # noqa: BLE001
            rec["success"] = False
            rec["errors"] = [traceback.format_exc()[-2000:]]
        rec["seconds"] = round(time.time() - t, 1)
        rec["peak_vram_gb"] = round(torch.cuda.max_memory_allocated() / 1e9, 2) if torch.cuda.is_available() else None
        report["tasks"].append(rec)
        save()
    shutil.rmtree(out / "raw", ignore_errors=True)
    save()
    return report


if __name__ == "__main__":
    if "REQUEST_JSON" in globals():  # Kaggle: request embedded by the dispatcher
        req = json.loads(globals()["REQUEST_JSON"])
        root, out = Path("/tmp/Wan2GP"), Path("/kaggle/working/out")
    else:
        import argparse

        ap = argparse.ArgumentParser()
        ap.add_argument("request", type=Path)
        ap.add_argument("--root", type=Path, required=True)
        ap.add_argument("--out", type=Path, required=True)
        a = ap.parse_args()
        req, root, out = json.loads(a.request.read_text()), a.root, a.out
    rep = run(req, root, out)
    print(json.dumps({k: v for k, v in rep.items() if k != "setup"}, indent=1)[:4000])
