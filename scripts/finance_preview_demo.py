"""Zero-network finance MP4 acceptance sample using the existing premium renderer.

No LLM calls, Telegram upload, publication, secrets, or production deployment.
All visuals are explicitly illustrative, not reported CPI data.
"""
from __future__ import annotations
import argparse
import json
import subprocess
from pathlib import Path
from tiktok_motion.premium_job import render

SCENES = [
    {"kind": "hero",
     "narration": "Inflation is not simply a number on a news headline. It describes how the prices of everyday goods change over time.",
     "on_screen": "WHY PRICES CHANGE", "items": ["INFLATION"], "camera": "push_in"},
    {"kind": "data",
     "narration": "Imagine a weekly grocery basket costing one hundred dollars. In this illustrative example, the same basket later costs one hundred and ten.",
     "on_screen": "ILLUSTRATIVE · GROCERY BASKET",
     "data": [{"label": "Before", "value": 100}, {"label": "After", "value": 110}],
     "camera": "pan_right"},
    {"kind": "document",
     "narration": "An illustrative receipt makes this easier to see. The basket contains the same products, but the total price has increased.",
     "on_screen": "A SAMPLE RECEIPT", "excerpt": "Basket A: $100 → $110",
     "source_label": "Illustrative example", "camera": "push_in"},
    {"kind": "data",
     "narration": "The difference is ten dollars. This chart is a hypothetical comparison, not official inflation data or a measurement of any real household.",
     "on_screen": "ILLUSTRATIVE · PRICE DIFFERENCE",
     "data": [{"label": "Earlier", "value": 100}, {"label": "Later", "value": 110}],
     "camera": "pan_left"},
    {"kind": "map",
     "narration": "Around the world, prices can change at different speeds. Geographic differences matter because countries buy, sell, and produce different things.",
     "on_screen": "A GLOBAL PATTERN", "camera": "orbit"},
    {"kind": "document",
     "narration": "Now picture a sample household budget. Rent, food, and transportation each take a share, while the available income stays unchanged.",
     "on_screen": "THE HOUSEHOLD BUDGET", "excerpt": "Rent · Food · Transportation",
     "source_label": "Illustrative example", "camera": "push_in"},
    {"kind": "data",
     "narration": "When essential costs rise, a family may need to adjust its choices. That does not mean every family's experience is identical.",
     "on_screen": "ILLUSTRATIVE · MONTHLY COSTS",
     "data": [{"label": "Rent", "value": 50}, {"label": "Food", "value": 30},
              {"label": "Transport", "value": 20}], "camera": "pan_right"},
    {"kind": "hero",
     "narration": "The important lesson is simple. To understand inflation, compare actual prices and income over time, and always check the source of the numbers.",
     "on_screen": "CHECK THE SOURCE", "items": ["CHECK THE FACTS"], "camera": "push_in"},
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=Path("outputs/finance-preview"))
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    request = {"profile": "premium", "visual_mode": "premium", "voice": "af_heart",
               "language": "en", "script": json.dumps(
                   {"language": "en", "title": "Inflation | a visual example", "scenes": SCENES},
                   ensure_ascii=False)}
    report = render(request, args.out)
    video = args.out / "final.mp4"
    probe = json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_format", "-show_streams",
        "-of", "json", str(video)], text=True))
    (args.out / "ffprobe.json").write_text(json.dumps(probe, indent=2))
    plan = json.loads((args.out / "plan.json").read_text())
    starts = []
    frame_no = 0
    for scene in plan["scenes"]:
        starts.append((scene["kind"], (frame_no + min(24, max(1, scene["durationFrames"] // 2))) / 30))
        frame_no += scene["durationFrames"]
    review = args.out / "review"
    review.mkdir(exist_ok=True)
    for i, (kind, seconds) in enumerate(starts):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(seconds),
                        "-i", str(video), "-frames:v", "1",
                        str(review / f"frame_{i + 1:02d}_{kind}.png")], check=True)
    report["target_duration_range"] = [58, 62]
    report["duration_in_target"] = 58 <= report["duration_seconds"] <= 62
    report["preview_only"] = True
    report["telegram_accepted"] = False
    (args.out / "report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({"duration": report["duration_seconds"],
                      "duration_in_target": report["duration_in_target"],
                      "scenes": len(plan["scenes"]), "kinds": [s["kind"] for s in plan["scenes"]]},
                     indent=2))


if __name__ == "__main__":
    main()
