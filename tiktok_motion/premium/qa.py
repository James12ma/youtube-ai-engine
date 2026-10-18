"""Technical validation for a rendered prototype MP4 (ffprobe/ffmpeg only).

Checks the delivery contract (1080x1920, 30 fps, duration, H.264/yuv420p, AAC audio),
detects black/frozen stretches and audio clipping, and exports five evidence frames.

    python qa.py out/focus_prototype.mp4 [--frames-dir out/frames]
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TL = json.loads((HERE / "timeline.json").read_text())
# Five representative moments: hero + dots, headline 1, dialog click, headline 2 + ring, end lockup.
EVIDENCE = {"01_open": 24, "02_doing_more": 96, "03_dialog_click": 158, "04_what_to_cut": 252, "05_more_impact": 380}


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, check=True)


def probe(path):
    out = run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)]).stdout
    return json.loads(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mp4", type=Path)
    ap.add_argument("--frames-dir", type=Path)
    a = ap.parse_args()
    info = probe(a.mp4)
    v = next(s for s in info["streams"] if s["codec_type"] == "video")
    au = [s for s in info["streams"] if s["codec_type"] == "audio"]
    num, den = map(int, v["r_frame_rate"].split("/"))
    dur = float(info["format"]["duration"])
    nb = int(v.get("nb_frames", 0))
    checks = {
        "resolution_1080x1920": (v["width"], v["height"]) == (TL["width"], TL["height"]),
        "fps_30": num / den == TL["fps"],
        "frame_count": nb == TL["frames"],
        "duration_10_15s": 10.0 <= dur <= 15.0,
        "codec_h264_yuv420p": v["codec_name"] == "h264" and v["pix_fmt"] == "yuv420p",
        "audio_aac": bool(au) and au[0]["codec_name"] == "aac",
    }
    black = run(["ffmpeg", "-v", "info", "-i", str(a.mp4), "-vf", "blackdetect=d=0.1:pix_th=0.1", "-an", "-f", "null", "-"]).stderr
    freeze = run(["ffmpeg", "-v", "info", "-i", str(a.mp4), "-vf", "freezedetect=n=0.0005:d=1.0", "-an", "-f", "null", "-"]).stderr
    vol = run(["ffmpeg", "-v", "info", "-i", str(a.mp4), "-af", "volumedetect", "-vn", "-f", "null", "-"]).stderr
    peak = re.search(r"max_volume: (-?[\d.]+) dB", vol)
    mean = re.search(r"mean_volume: (-?[\d.]+) dB", vol)
    checks["no_black_segments"] = "black_start" not in black
    checks["no_freeze_over_1s"] = "freeze_start" not in freeze
    checks["audio_not_clipping"] = bool(peak) and float(peak.group(1)) < -0.5
    report = {
        "file": str(a.mp4),
        "size_mb": round(a.mp4.stat().st_size / 1e6, 2),
        "width": v["width"], "height": v["height"], "fps": num / den, "frames": nb, "duration_s": round(dur, 3),
        "video_bitrate_kbps": round(int(v.get("bit_rate", 0)) / 1000),
        "audio_peak_db": float(peak.group(1)) if peak else None,
        "audio_mean_db": float(mean.group(1)) if mean else None,
        "checks": checks,
        "passed": all(checks.values()),
    }
    frames_dir = a.frames_dir or a.mp4.parent / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    for name, f in EVIDENCE.items():
        run(["ffmpeg", "-v", "error", "-y", "-i", str(a.mp4), "-vf", f"select=eq(n\\,{f})", "-frames:v", "1",
             str(frames_dir / f"{name}_f{f:03d}.png")])
    report["evidence_frames"] = sorted(p.name for p in frames_dir.glob("*.png"))
    print(json.dumps(report, indent=2))
    (a.mp4.parent / "qa_report.json").write_text(json.dumps(report, indent=2))
    sys.exit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
