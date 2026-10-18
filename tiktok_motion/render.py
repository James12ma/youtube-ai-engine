"""Offline 2D animated demo renderer. Requires Pillow and FFmpeg.

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

from .storyboard import build_demo, full_narration_text

W, H = 1080, 1920
BG = (250, 249, 246)
INK = (21, 21, 21)
ACCENT = (230, 51, 54)
MUTED = (187, 187, 187)
WHITE = (255, 255, 255)


def _font(size: int):
    from PIL import ImageFont
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def _wrap(draw, text: str, font, max_w: int) -> list[str]:
    words = text.split()
    lines, line = [], ""
    for word in words:
        candidate = (line + " " + word).strip()
        if draw.textbbox((0, 0), candidate, font=font)[2] > max_w and line:
            lines.append(line)
            line = word
        else:
            line = candidate
    if line:
        lines.append(line)
    return lines


def _ease(t: float) -> float:
    # smoothstep
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def _draw_hook(d, im, local: float, fonts):
    """Bold kinetic type + disconnect icon."""
    big, mid, small, tiny = fonts
    # Pulsing disconnect icon (circle with slash)
    cx, cy = W // 2, 720
    pulse = 1.0 + 0.08 * math.sin(local * 6)
    r = int(140 * pulse)
    d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=ACCENT, width=14)
    # Slash
    d.line((cx - int(90 * pulse), cy + int(90 * pulse),
            cx + int(90 * pulse), cy - int(90 * pulse)), fill=ACCENT, width=16)
    # WiFi arcs fading
    for i, rad in enumerate([180, 230, 280]):
        alpha_scale = max(0.2, 1.0 - local * 0.3 - i * 0.15)
        # approximate with arcs via ellipses partial
        d.arc((cx - rad, cy - rad + 40, cx + rad, cy + rad + 40),
              start=220, end=320, fill=MUTED, width=8)


def _draw_map(d, im, local: float, fonts):
    """Simplified world map with fading network links."""
    cx, cy = W // 2, 780
    # Continents as rounded blobs (stylized)
    continents = [
        (cx - 280, cy - 80, 180, 220),   # Americas-ish
        (cx + 40, cy - 120, 200, 160),   # Europe/Africa
        (cx + 220, cy - 40, 160, 180),   # Asia
        (cx + 180, cy + 140, 100, 80),   # Australia
    ]
    for x, y, w, h in continents:
        d.rounded_rectangle((x, y, x + w, y + h), radius=40, outline=INK, width=6)
    # Network nodes + fading links
    nodes = [
        (cx - 200, cy - 20), (cx - 80, cy + 60), (cx + 60, cy - 60),
        (cx + 200, cy + 20), (cx + 120, cy + 120), (cx - 40, cy - 100),
    ]
    fade = max(0.0, 1.0 - local / 8.0)
    for i, (x, y) in enumerate(nodes):
        d.ellipse((x - 12, y - 12, x + 12, y + 12), fill=ACCENT if fade > 0.3 else MUTED)
        for j in range(i + 1, len(nodes)):
            if (i + j) % 3 == 0:
                col = tuple(int(c * fade + m * (1 - fade)) for c, m in zip(ACCENT, MUTED))
                d.line((x, y, *nodes[j]), fill=col, width=3)
    # Expanding offline rings
    for j in range(3):
        rad = int(80 + local * 40 + j * 50)
        d.ellipse((cx - rad, cy - rad, cx + rad, cy + rad), outline=ACCENT, width=4)


def _draw_devices(d, im, local: float, fonts):
    """Phone + payment terminal with red X."""
    # Phone body
    px, py = 220, 520
    d.rounded_rectangle((px, py, px + 280, py + 520), radius=36, outline=INK, width=10, fill=WHITE)
    d.rectangle((px + 30, py + 50, px + 250, py + 420), fill=(240, 240, 240))
    d.ellipse((px + 120, py + 460, px + 160, py + 500), outline=INK, width=4)
    # X over phone
    t = _ease(min(1.0, local / 2.0))
    if t > 0:
        d.line((px + 40, py + 80, px + 240, py + 380), fill=ACCENT, width=int(14 * t))
        d.line((px + 240, py + 80, px + 40, py + 380), fill=ACCENT, width=int(14 * t))
    # Payment terminal
    tx, ty = 580, 620
    d.rounded_rectangle((tx, ty, tx + 320, ty + 280), radius=20, outline=INK, width=10, fill=WHITE)
    d.rectangle((tx + 30, ty + 30, tx + 290, ty + 140), fill=INK)
    # Card slot
    d.rectangle((tx + 60, ty + 180, tx + 260, ty + 210), fill=MUTED)
    # Spinner dots turning into X
    for k in range(4):
        a = local * 2 + k * math.pi / 2
        dx = int(40 * math.cos(a))
        dy = int(40 * math.sin(a))
        d.ellipse((tx + 160 + dx - 8, ty + 80 + dy - 8,
                   tx + 160 + dx + 8, ty + 80 + dy + 8), fill=ACCENT)


def _draw_systems(d, im, local: float, fonts):
    """Icons for store / logistics / services + counters."""
    icons = [
        (180, 580, "STORE"),
        (540, 580, "LOGISTICS"),
        (180, 980, "BANK"),
        (540, 980, "TRANSIT"),
    ]
    for i, (x, y, label) in enumerate(icons):
        bounce = int(8 * math.sin(local * 3 + i))
        d.rounded_rectangle((x, y + bounce, x + 320, y + 280 + bounce),
                            radius=28, outline=INK, width=8, fill=WHITE)
        d.ellipse((x + 110, y + 60 + bounce, x + 210, y + 160 + bounce),
                  outline=ACCENT, width=10)
        # counter number rising
        count = int(min(99, local * 8 + i * 7))
        d.text((x + 100, y + 180 + bounce), f"{count:02d}", font=fonts[1], fill=ACCENT)
        d.text((x + 70, y + 230 + bounce), label, font=fonts[2], fill=INK)


def _draw_nuance(d, im, local: float, fonts):
    """Offline-capable tools highlighted."""
    items = [
        (W // 2, 620, "RADIO"),
        (280, 920, "CASH"),
        (800, 920, "LOCAL NET"),
        (W // 2, 1220, "PAPER MAPS"),
    ]
    for i, (x, y, label) in enumerate(items):
        appear = _ease(max(0.0, min(1.0, (local - i * 0.6) / 1.2)))
        if appear <= 0:
            continue
        r = max(30, int(90 * appear))
        d.ellipse((x - r, y - r, x + r, y + r), outline=ACCENT, width=10)
        if r > 25:
            d.ellipse((x - r + 20, y - r + 20, x + r - 20, y + r - 20), fill=BG)
        # label
        bbox = d.textbbox((0, 0), label, font=fonts[2])
        tw = bbox[2] - bbox[0]
        d.text((x - tw // 2, y + r + 20), label, font=fonts[2], fill=INK)


def _draw_outro(d, im, local: float, fonts):
    """High contrast question."""
    # Large pulsing question mark
    cx, cy = W // 2, 780
    pulse = 1.0 + 0.06 * math.sin(local * 4)
    r = int(160 * pulse)
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=ACCENT)
    d.text((cx - 40, cy - 90), "?", font=fonts[0], fill=WHITE)


SCENE_DRAW = {
    "hook": _draw_hook,
    "map": _draw_map,
    "devices": _draw_devices,
    "systems": _draw_systems,
    "nuance": _draw_nuance,
    "outro": _draw_outro,
}


def render(output: Path, voice: Path | None = None, fps: int = 30) -> Path:
    try:
        from PIL import Image, ImageDraw
    except ImportError as exc:
        raise RuntimeError("Install Pillow to render the video: pip install Pillow") from exc
    if not shutil.which("ffmpeg"):
        raise RuntimeError("FFmpeg is required on PATH")
    if voice is not None and not voice.is_file():
        raise FileNotFoundError(voice)

    data = build_demo()
    scenes = data["scenes"]
    fonts = (_font(96), _font(52), _font(32), _font(28))
    big, mid, small, tiny = fonts

    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="tiktok-motion-") as tmp:
        silent = Path(tmp) / "silent.mp4"
        pipe = subprocess.Popen(
            [
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-f", "rawvideo", "-pixel_format", "rgb24",
                "-video_size", f"{W}x{H}", "-framerate", str(fps),
                "-i", "-",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                "-pix_fmt", "yuv420p", "-an", str(silent),
            ],
            stdin=subprocess.PIPE,
        )
        try:
            for frame in range(60 * fps):
                sec = frame / fps
                scene = next(s for s in scenes if s["start_seconds"] <= sec < s["end_seconds"])
                local = sec - scene["start_seconds"]
                im = Image.new("RGB", (W, H), BG)
                d = ImageDraw.Draw(im)

                # Top accent bar
                d.rectangle((0, 0, W, 28), fill=ACCENT)
                # Brand label
                d.text((60, 60), "THE 60-SECOND EXPLAINER", font=tiny, fill=INK)
                d.line((60, 105, 1020, 105), fill=ACCENT, width=5)

                # Scene-specific motion graphic
                drawer = SCENE_DRAW.get(scene["kind"], _draw_hook)
                drawer(d, im, local, fonts)

                # Caption card
                card_top = 1480
                d.rounded_rectangle((48, card_top, W - 48, 1780), radius=32, fill=INK)
                lines = _wrap(d, scene["on_screen_text"], mid, 900)
                for i, text in enumerate(lines[:3]):
                    d.text((80, card_top + 40 + i * 70), text, font=mid, fill=WHITE)

                # Disclaimer footer
                d.text((60, 1820), "HYPOTHETICAL  •  NOT REAL NEWS", font=tiny, fill=INK)

                # Progress bar
                progress = sec / 60.0
                d.rectangle((0, 1895, int(W * progress), 1920), fill=ACCENT)

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

        if voice is None:
            shutil.copyfile(silent, output)
        else:
            subprocess.run(
                [
                    "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                    "-i", str(silent), "-i", str(voice),
                    "-map", "0:v:0", "-map", "1:a:0",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
                    "-af", "apad", "-t", "60", str(output),
                ],
                check=True,
            )
    return output


def generate_narration(wav_path: Path) -> Path:
    """Zero-cost English narration via espeak-ng (engineering voice)."""
    text = full_narration_text()
    wav_path = wav_path.resolve()
    wav_path.parent.mkdir(parents=True, exist_ok=True)
    # espeak-ng: English, moderate speed for clarity
    cmd = [
        "espeak-ng", "-v", "en-us", "-s", "145", "-w", str(wav_path), text
    ]
    subprocess.run(cmd, check=True)
    return wav_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("tiktok-demo-001.mp4"))
    parser.add_argument("--voice", type=Path)
    parser.add_argument("--generate-voice", action="store_true",
                        help="Generate engineering espeak narration and mux it")
    parser.add_argument("--fps", type=int, default=30)
    args = parser.parse_args()
    if args.fps <= 0:
        parser.error("--fps must be positive")
    voice = args.voice
    if args.generate_voice:
        voice = Path(tempfile.gettempdir()) / "tiktok_narration.wav"
        generate_narration(voice)
        print(f"Narration: {voice}")
    out = render(args.output, voice, args.fps)
    print(out)


if __name__ == "__main__":
    main()
