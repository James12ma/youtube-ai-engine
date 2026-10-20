"""YouTube AI Engine offline production entrypoint (no upload or paid APIs).

Run from repository root:
  python -m tiktok_motion.produce --topic job-interviews --output /tmp/career.mp4

This is a narrow production proof, NOT an open-ended AI topic/script generator.
Only registered subjects can render; unsupported topics fail explicitly.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from .career_motion import render_career

TOPICS = {
    "job-interviews": {
        "title": "5 Types of Job Interviews",
        "language": "en",
        "type": "career_education",
        "format": "vertical_short",
        "duration_seconds": 60,
        "engine": "tiktok_motion.career_motion",
        "requires_owner_approval": True,
        "auto_publish": False,
    }
}

INTERVIEW_SCRIPT = (
    "There are five interview formats you should prepare for. "
    "First, an in-person interview. Arrive early, bring your resume, and make eye contact. "
    "Second, a phone screening. Choose a quiet room and keep your notes close. "
    "Third, a video interview. Test your camera, microphone, and lighting before the call. "
    "Fourth, a panel interview. Answer the person who asks, then include the rest of the room. "
    "Fifth, a skills assessment. Explain your thinking while showing how you solve a real task. "
    "Different formats reward different preparation. Save this guide before your next interview."
)

def normalize_topic(value: str) -> str:
    k = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    aliases = {
        "5-types-of-job-interviews": "job-interviews",
        "types-of-job-interviews": "job-interviews",
        "interview-types": "job-interviews",
    }
    return aliases.get(k, k)

def _ffprobe(path: Path) -> dict:
    p = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
                       capture_output=True, text=True, check=True)
    return json.loads(p.stdout)

def _add_engineering_voice(original: Path, destination: Path, *, preview: bool) -> None:
    """Optional local speech; engineering-grade, not premium neural TTS."""
    engine = shutil.which("espeak-ng") or shutil.which("espeak")
    if not engine:
        raise RuntimeError("Requested espeak narration, but neither espeak-ng nor espeak is installed")
    with tempfile.TemporaryDirectory(prefix="yt-engine-voice-") as tmp:
        wav = Path(tmp) / "narration.wav"
        subprocess.run([engine, "-v", "en-us", "-s", "150", "-w", str(wav), INTERVIEW_SCRIPT],
                       check=True, capture_output=True, text=True)
        duration = "4" if preview else "60"
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(original), "-i", str(wav),
                        "-filter_complex", "[0:a]volume=0.13[m];[1:a]volume=1.8[v];[m][v]amix=inputs=2:duration=first:dropout_transition=0,alimiter=limit=0.92[a]",
                        "-map", "0:v:0", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-t", duration,
                        "-movflags", "+faststart", str(destination)], check=True, capture_output=True, text=True)

def produce(topic: str, output: str | Path, *, preview: bool = False, voice: str = "none") -> dict:
    """Start-to-finish render with evidence JSON manifest. Never uploads or publishes."""
    topic_id = normalize_topic(topic)
    if topic_id not in TOPICS:
        raise ValueError(f"Unsupported topic {topic!r}; supported: {', '.join(TOPICS)}. No fabricated AI script.")
    if voice not in ("none", "espeak"):
        raise ValueError("voice must be 'none' or 'espeak'")
    output = Path(output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="youtube-ai-engine-") as tmp:
        intermediate = Path(tmp) / "career_base.mp4" if voice == "espeak" else output
        render_career(intermediate, preview=preview, music_enabled=True)
        if voice == "espeak":
            _add_engineering_voice(intermediate, output, preview=preview)
    probed = _ffprobe(output)
    v = next((s for s in probed["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in probed["streams"] if s["codec_type"] == "audio"), None)
    expected_duration = 4 if preview else 60
    duration = float(probed["format"]["duration"])
    passed = bool(v and a and v["codec_name"] == "h264" and a["codec_name"] == "aac"
                  and v["width"] == 1080 and v["height"] == 1920 and abs(duration-expected_duration) < 0.20)
    manifest = {
        "producer": "James12ma/youtube-ai-engine:tiktok_motion.produce",
        "topic_id": topic_id,
        **TOPICS[topic_id],
        "render_status": "passed" if passed else "failed",
        "output": str(output),
        "duration_measured_seconds": round(duration, 3),
        "fps_measured": v["r_frame_rate"] if v else None,
        "video_codec": v["codec_name"] if v else None,
        "audio_codec": a["codec_name"] if a else None,
        "video_generation": "procedural_animated_2D_with_upscale",
        "voice": "espeak_engineering_not_neural" if voice == "espeak" else "none_music_only",
        "ai_director_enabled": False,
        "natural_voice_enabled": False,
        "premium_quality_owner_approved": False,
        "requires_owner_approval": True,
        "auto_publish": False,
    }
    report = output.with_suffix(".engine_run.json")
    report.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    if not passed:
        raise RuntimeError(f"Engine output failed technical QA. See {report}")
    return manifest

def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="YouTube AI Engine: offline, owner-reviewed vertical video production")
    parser.add_argument("--topic", required=True, help="Registered topic, currently: job-interviews")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--preview", action="store_true", help="Render just first 4 seconds")
    parser.add_argument("--voice", choices=("none", "espeak"), default="none",
                        help="espeak is robotic engineering TTS; omit for instrumental music only")
    args = parser.parse_args(argv)
    print(json.dumps(produce(args.topic, args.output, preview=args.preview, voice=args.voice), indent=2))

if __name__ == "__main__":
    main()
