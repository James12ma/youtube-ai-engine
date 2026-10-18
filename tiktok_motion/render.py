"""Offline 2D animated demo renderer. Requires Pillow and FFmpeg installed locally.

No network calls, billing, upload, or automatic publication.
Usage: python -m tiktok_motion.render --output /tmp/tiktok-demo.mp4
Optional: --voice /path/to/approved_english_narration.wav
"""
from __future__ import annotations

import argparse
import math
import shutil
import subprocess
import tempfile
from pathlib import Path

from .storyboard import build_demo

W, H = 1080, 1920


def render(output: Path, voice: Path | None = None, fps: int = 30) -> Path:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as exc:
        raise RuntimeError("Install Pillow to render the video: pip install Pillow") from exc
    if not shutil.which("ffmpeg"):
        raise RuntimeError("FFmpeg is required on PATH")
    if voice is not None and not voice.is_file():
        raise FileNotFoundError(voice)
    data = build_demo()
    scenes = data["scenes"]
    def font(size: int):
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
        ]
        for candidate in candidates:
            if Path(candidate).exists():
                return ImageFont.truetype(candidate, size)
        return ImageFont.load_default()
    big, small = font(83), font(39)
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="tiktok-motion-") as tmp:
        pipe = subprocess.Popen(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
             "-f", "rawvideo", "-pixel_format", "rgb24", "-video_size", f"{W}x{H}",
             "-framerate", str(fps), "-i", "-",
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
             "-pix_fmt", "yuv420p", "-an", str(Path(tmp) / "silent.mp4")],
            stdin=subprocess.PIPE,
        )
        try:
            for frame in range(60 * fps):
                sec = frame / fps
                scene = next(s for s in scenes if s["start_seconds"] <= sec < s["end_seconds"])
                local = sec - scene["start_seconds"]
                im = Image.new("RGB", (W, H), "#FAF9F6")
                d = ImageDraw.Draw(im)
                d.rectangle((0, 0, W, 30), fill="#E63336")
                d.text((75, 115), "THE 60-SECOND EXPLAINER", font=small, fill="#151515")
                d.line((75, 205, 1005, 205), fill="#E63336", width=7)
                # Animated editorial graphic: concentric rings, network nodes and links.
                cx, cy = W // 2, 840
                for j in range(3):
                    radius = 170 + j * 95 + int(12 * math.sin(local * 2 + j))
                    d.ellipse((cx-radius, cy-radius, cx+radius, cy+radius),
                              outline="#E63336" if j == 0 else "#151515", width=9)
                nodes = []
                for k in range(8):
                    a = 2 * math.pi * k / 8 + local * 0.16
                    x, y = cx + int(370 * math.cos(a)), cy + int(370 * math.sin(a))
                    nodes.append((x, y))
                    d.ellipse((x-16, y-16, x+16, y+16), fill="#E63336")
                for i in range(8):
                    d.line((cx, cy, *nodes[i]), fill="#BBBBBB", width=4)
                d.rounded_rectangle((65, 1330, 1015, 1660), radius=38, fill="#151515")
                words = scene["on_screen_text"].split()
                lines, line = [], ""
                for word in words:
                    candidate = (line + " " + word).strip()
                    if d.textbbox((0, 0), candidate, font=big)[2] > 810 and line:
                        lines.append(line)
                        line = word
                    else:
                        line = candidate
                if line:
                    lines.append(line)
                for i, text in enumerate(lines):
                    d.text((110, 1380 + i * 98), text, font=big, fill="#FFFFFF")
                d.text((80, 1750), "HYPOTHETICAL SCENARIO  •  NOT REAL NEWS", font=small, fill="#151515")
                d.rectangle((0, 1885, int(W * sec / 60), 1920), fill="#E63336")
                assert pipe.stdin is not None
                pipe.stdin.write(im.tobytes())
        except (BrokenPipeError, OSError):
            pipe.kill()
            raise RuntimeError("FFmpeg video encoder failed")
        finally:
            if pipe.stdin:
                pipe.stdin.close()
        if pipe.wait() != 0:
            raise RuntimeError("FFmpeg returned nonzero exit status")
        silent = Path(tmp) / "silent.mp4"
        if voice is None:
            shutil.copyfile(silent, output)
        else:
            subprocess.run(
                ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                 "-i", str(silent), "-i", str(voice), "-map", "0:v:0", "-map", "1:a:0",
                 "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-af", "apad",
                 "-t", "60", str(output)],
                check=True,
            )
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("tiktok-demo-001.mp4"))
    parser.add_argument("--voice", type=Path)
    parser.add_argument("--fps", type=int, default=30)
    args = parser.parse_args()
    if args.fps <= 0:
        parser.error("--fps must be positive")
    print(render(args.output, args.voice, args.fps))


if __name__ == "__main__":
    main()
