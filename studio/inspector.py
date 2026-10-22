"""Quality Inspector: finds observable defects in a rendered film. It reports; it never approves.

Checks: delivery format (size, fps, H.264 yuv420p BT.709, AAC), duration vs plan, black or frozen
stretches, loudness for social platforms (-14 LUFS integrated, true peak below -1 dBTP), and spec
coverage (real voice timing, no pending assets, every beat inside its shot). Writes a labelled
contact sheet with one frame per story beat so a human can judge whether each beat reads.

    python -m studio.inspector film.mp4 --plan studio/editor/public/plan.json --out report_dir
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

LUFS_TARGET, LUFS_TOL, TRUE_PEAK_MAX = -14.0, 1.5, -1.0


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True)


def probe(mp4: Path) -> dict:
    return json.loads(_run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(mp4)]).stdout)


def loudness(mp4: Path) -> dict:
    err = _run(["ffmpeg", "-hide_banner", "-i", str(mp4), "-af", "ebur128=peak=true", "-f", "null", "-"]).stderr
    tail = err[err.rfind("Summary:"):]
    i = re.search(r"I:\s+(-?[\d.]+) LUFS", tail)
    tp = re.search(r"Peak:\s+(-?[\d.]+) dBFS", tail)
    return {"integrated_lufs": float(i.group(1)) if i else None, "true_peak_dbtp": float(tp.group(1)) if tp else None}


def master_audio(src: Path, dst: Path) -> dict:
    """Two-pass EBU R128 loudness normalisation to the social target; video stream copied untouched."""
    first = _run(["ffmpeg", "-hide_banner", "-i", str(src), "-af",
                  f"loudnorm=I={LUFS_TARGET}:TP={TRUE_PEAK_MAX - 0.5}:LRA=11:print_format=json", "-f", "null", "-"]).stderr
    m = json.loads(first[first.rfind("{"):first.rfind("}") + 1])
    af = (f"loudnorm=I={LUFS_TARGET}:TP={TRUE_PEAK_MAX - 0.5}:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
          f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    r = _run(["ffmpeg", "-y", "-hide_banner", "-i", str(src), "-c:v", "copy", "-af", af, "-ar", "48000",
              "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(dst)])
    if r.returncode:
        raise RuntimeError(r.stderr[-800:])
    return {"before_lufs": float(m["input_i"])}


def inspect(mp4: Path, plan: dict, out: Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    info = probe(mp4)
    v = next(s for s in info["streams"] if s["codec_type"] == "video")
    a = [s for s in info["streams"] if s["codec_type"] == "audio"]
    num, den = map(int, v["r_frame_rate"].split("/"))
    dur = float(info["format"]["duration"])
    defects: list[str] = []

    def check(ok: bool, msg: str):
        if not ok:
            defects.append(msg)

    check((v["width"], v["height"]) == (plan["width"], plan["height"]), f"size {v['width']}x{v['height']} != plan")
    check(num / den == plan["fps"], f"fps {num / den} != {plan['fps']}")
    check(v["codec_name"] == "h264" and v.get("pix_fmt") == "yuv420p", f"video {v['codec_name']}/{v.get('pix_fmt')} (need h264/yuv420p)")
    check(v.get("color_space") in (None, "bt709") and v.get("color_range") != "pc", f"colour {v.get('color_space')}/{v.get('color_range')} (need bt709 tv)")
    check(bool(a) and a[0]["codec_name"] == "aac", "no AAC audio track")
    check(abs(dur - plan["durationInFrames"] / plan["fps"]) < 0.2, f"duration {dur:.2f}s differs from plan")
    black = _run(["ffmpeg", "-i", str(mp4), "-vf", "blackdetect=d=0.25:pix_th=0.08", "-an", "-f", "null", "-"]).stderr
    check("black_start" not in black, "black stretch >= 0.25 s")
    freeze = _run(["ffmpeg", "-i", str(mp4), "-vf", "freezedetect=n=0.0008:d=1.2", "-an", "-f", "null", "-"]).stderr
    frozen = re.findall(r"freeze_start: ([\d.]+)", freeze)
    check(not frozen, f"frozen picture >= 1.2 s at {frozen[:4]} s (static hold)")
    loud = loudness(mp4) if a else {}
    if loud.get("integrated_lufs") is not None:
        check(abs(loud["integrated_lufs"] - LUFS_TARGET) <= LUFS_TOL, f"loudness {loud['integrated_lufs']} LUFS (target {LUFS_TARGET})")
        check(loud["true_peak_dbtp"] is None or loud["true_peak_dbtp"] <= TRUE_PEAK_MAX, f"true peak {loud['true_peak_dbtp']} dBTP")
    check(not plan.get("preview_timing"), "timing is estimated, not from the real voice")
    check(not plan.get("missing_assets"), f"pending assets: {plan.get('missing_assets')}")
    for s in plan["shots"]:
        for b in s["beats"]:
            check(s["from"] <= b["frame"] < s["to"], f"{s['id']}: beat '{b['action']}' at frame {b['frame']} outside its shot")
    # One frame per beat (6 frames after it lands) for a human to judge whether it reads.
    picks = [(min(b["frame"] + 6, s["to"] - 1), f"{s['id']} {b['action']}"[:40]) for s in plan["shots"] for b in s["beats"]]
    picks = picks or [((s["from"] + s["to"]) // 2, s["id"]) for s in plan["shots"]]
    sheet = out / "beats_sheet.png"
    sel = "+".join(f"eq(n\\,{f})" for f, _ in picks)
    labels = ",".join(f"drawtext=text='{t.replace(chr(39), '')}':enable='eq(n\\,{f})':x=10:y=10:fontsize=34:fontcolor=white:box=1:boxcolor=black@0.6"
                      for f, t in picks)
    cols = min(8, len(picks))
    rows = -(-len(picks) // cols)
    _run(["ffmpeg", "-v", "error", "-y", "-i", str(mp4), "-vf", f"{labels},select='{sel}',scale=270:-1,tile={cols}x{rows}",
          "-frames:v", "1", "-vsync", "vfr", str(sheet)])
    report = {"file": str(mp4), "duration_s": round(dur, 3), "width": v["width"], "height": v["height"], "fps": num / den,
              "loudness": loud, "beats_checked": len(picks), "defects": defects, "technically_clean": not defects,
              "owner_acceptance": "required (the Inspector never approves)", "beats_sheet": sheet.name}
    (out / "inspection.json").write_text(json.dumps(report, indent=1))
    return report


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("mp4", type=Path)
    ap.add_argument("--plan", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    print(json.dumps(inspect(a.mp4, json.loads(a.plan.read_text()), a.out), indent=1))
