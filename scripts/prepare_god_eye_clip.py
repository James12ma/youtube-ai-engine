"""Prepare an owner-reviewed God's Eye View (Cesium) silent capture for Remotion.

This step accepts ONLY a locally supplied video. It does not run, fork, clone,
scrape, or download upstream imagery, and does not use billable mapping APIs.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

PUBLIC = Path(__file__).resolve().parents[1] / "tiktok_motion/premium/remotion/public/job"


def prepare(source: Path, clip_id: str, *, attribution: str, commercial_approved: bool,
            output_dir: Path = PUBLIC) -> dict:
    if not re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", clip_id):
        raise ValueError("Invalid geographic clip ID")
    if not commercial_approved:
        raise ValueError("Commercial imagery/data license review is required before ingestion")
    if not attribution.strip() or len(attribution) > 160:
        raise ValueError("Source attribution required")
    if not source.is_file() or source.stat().st_size <= 0:
        raise ValueError("Source must be a locally reviewed video file")
    info = json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_format", "-show_streams",
        "-of", "json", str(source)], text=True))
    video = next((s for s in info["streams"] if s.get("codec_type") == "video"), None)
    duration = float(info.get("format", {}).get("duration") or 0)
    if not video or not (1 <= duration <= 30):
        raise ValueError("Reviewed capture must have 1–30 seconds of video")
    output_dir.mkdir(parents=True, exist_ok=True)
    destination = output_dir / f"god_eye_{clip_id}.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-i", str(source), "-an",
        "-vf", "scale=1080:690:force_original_aspect_ratio=increase,crop=1080:690",
        "-r", "30", "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", str(destination),
    ], check=True)
    return {
        "kind": "god_eye",
        "geo_clip": f"job/god_eye_{clip_id}.mp4",
        "geo_attribution": attribution.strip(),
        "duration_seconds": duration,
        "requires_owner_approval": True,
        "auto_publish": False,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("source", type=Path)
    p.add_argument("--clip-id", required=True)
    p.add_argument("--attribution", required=True)
    p.add_argument("--commercial-license-reviewed", action="store_true")
    args = p.parse_args()
    print(json.dumps(prepare(args.source, args.clip_id,
        attribution=args.attribution,
        commercial_approved=args.commercial_license_reviewed), indent=2))


if __name__ == "__main__":
    main()
