"""Non-semantic visual difference smoke test; never a creative-quality pass."""
from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path
from PIL import Image


def frame(video: Path, second: float, target: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-ss", str(second), "-i", str(video),
                    "-frames:v", "1", "-vf", "scale=270:480", str(target)],
                   check=True, capture_output=True)
    return target


def dhash64(image: Path) -> int:
    im = Image.open(image).convert("L").resize((9, 8), Image.Resampling.LANCZOS)
    pixels = list(im.getdata())
    result = 0
    for row in range(8):
        for col in range(8):
            pos = 9 * row + col
            result = (result << 1) | int(pixels[pos] > pixels[pos + 1])
    return result


def verify(video: Path, samples: list[tuple[str, float]], output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    frames = [(kind, frame(video, t, output / f"{kind}_{i}.png"))
              for i, (kind, t) in enumerate(samples)]
    hashes = [(kind, dhash64(path)) for kind, path in frames]
    pairs = [{"a": a, "b": b, "hamming": (ha ^ hb).bit_count()}
             for i, (a, ha) in enumerate(hashes)
             for b, hb in hashes[i + 1:]]
    result = {
        "frames": [{"kind": kind, "path": str(path)} for kind, path in frames],
        "pairs": pairs,
        "min_hamming": min((p["hamming"] for p in pairs), default=0),
        "threshold": 15,
        "passed_visual_difference": bool(pairs) and all(p["hamming"] >= 15 for p in pairs),
        "is_semantic_qa": False,
        "requires_human_review": True,
    }
    (output / "style_report.json").write_text(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("usage: python -m tests.verify_style_distinctness video.mp4 [timestamps...]")
    times = [float(x) for x in sys.argv[2:]] or [3, 18, 30, 45]
    report = verify(Path(sys.argv[1]),
                    [(f"scene{i + 1}", t) for i, t in enumerate(times)],
                    Path("review"))
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["passed_visual_difference"] else 1)
