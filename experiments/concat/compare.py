"""Measure two renders of timeline.json the same way. Usage: compare.py OUT_DIR concat.mp4 baseline.mp4"""
import difflib
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

here = Path(__file__).resolve().parent
out = Path(sys.argv[1]).resolve()
out.mkdir(parents=True, exist_ok=True)
renders = {"concat": Path(sys.argv[2]), "baseline": Path(sys.argv[3])}
tl = json.loads((here / "timeline.json").read_text())
CUTS = [c["start_s"] for c in tl["clips"][1:]]
SHEET_T = [1.5, 2.9, 3.2, 4.5, 6.2, 7.5, 9.2, 10.5, 12.2, 13.5]


def sh(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def grab(path, t, w=270):
    p = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", str(path), "-frames:v", "1", "-f", "rawvideo",
                        "-pix_fmt", "rgb24", "-vf", f"scale={w}:{w * 16 // 9}", "-"], capture_output=True)
    return np.frombuffer(p.stdout, np.uint8).reshape(w * 16 // 9, w, 3).astype(np.float32)


def probe(path):
    p = json.loads(sh(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)]).stdout)
    v = next(s for s in p["streams"] if s["codec_type"] == "video")
    a = next((s for s in p["streams"] if s["codec_type"] == "audio"), None)
    return {"duration_s": round(float(p["format"]["duration"]), 3), "size_mb": round(int(p["format"]["size"]) / 1e6, 2),
            "video": {k: v.get(k) for k in ("codec_name", "width", "height", "r_frame_rate", "pix_fmt", "color_range",
                                            "color_primaries", "color_transfer", "nb_frames", "bit_rate")},
            "audio": a and {k: a.get(k) for k in ("codec_name", "sample_rate", "channels", "duration")}}


def loudness(path):
    e = sh(["ffmpeg", "-nostats", "-i", str(path), "-af", "ebur128=peak=true", "-f", "null", "-"]).stderr
    i = re.findall(r"I:\s+(-?[\d.]+) LUFS", e)
    tp = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", e)
    return {"integrated_lufs": float(i[-1]) if i else None, "true_peak_dbtp": float(tp[-1]) if tp else None}


def black(path):
    e = sh(["ffmpeg", "-i", str(path), "-vf", "blackdetect=d=0.1:pix_th=0.08", "-an", "-f", "null", "-"]).stderr
    return re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", e)


def window(path, t0, dur, w=216):
    h = w * 16 // 9
    p = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t0:.3f}", "-t", f"{dur:.3f}", "-i", str(path), "-f", "rawvideo",
                        "-pix_fmt", "gray", "-vf", f"scale={w}:{h}", "-"], capture_output=True)
    return np.frombuffer(p.stdout, np.uint8).reshape(-1, h, w).astype(np.float32)


def band(frames):
    h = frames.shape[1]
    return frames[:, int(h * 0.70):int(h * 0.95)]  # below every title position


def transitions(path):
    """Classify every frame within 0.6 s of each cut against the true source frames at that instant:
    'A' (outgoing shot), 'B' (incoming shot) or 'mixed' (a blend/wipe/slide in progress). Motion-proof,
    because the reference is the source itself. `mixed_frames` ~ 0 means a hard cut."""
    res = []
    for k, cut in enumerate(CUTS):
        a_clip, b_clip = tl["clips"][k], tl["clips"][k + 1]
        t0, dur = cut - 0.6, 1.2
        out_f = band(window(path, t0, dur))
        n = len(out_f)
        a_f = band(window(here / a_clip["source"], t0 - a_clip["start_s"], dur))[:n]
        b_start = t0 - b_clip["start_s"]
        b_f = band(window(here / b_clip["source"], max(0.0, b_start), dur + min(0.0, b_start)))
        pad = n - len(b_f)
        b_f = np.concatenate([np.repeat(b_f[:1], pad, axis=0), b_f]) if pad > 0 else b_f[:n]
        labels = []
        for i in range(min(n, len(a_f), len(b_f))):
            da, db = np.abs(out_f[i] - a_f[i]).mean(), np.abs(out_f[i] - b_f[i]).mean()
            labels.append("A" if da < 6 and da <= db else "B" if db < 6 else "mixed")
        mixed = [round(t0 + i / tl["fps"], 3) for i, l in enumerate(labels) if l == "mixed"]
        res.append({"cut_s": cut, "mixed_frames": len(mixed), "mixed_from_s": mixed[0] if mixed else None,
                    "mixed_to_s": mixed[-1] if mixed else None, "sequence": "".join(l[0] for l in labels)})
    return res


def ocr_titles(path, tag):
    rows = []
    for c in tl["clips"]:
        t = c["title"]
        mid = (t["at_s"] + t["until_s"]) / 2
        png = out / f"ocr_{tag}_{mid:05.2f}.png"
        sh(["ffmpeg", "-y", "-v", "error", "-ss", f"{mid}", "-i", str(path), "-frames:v", "1", str(png)])
        txt = sh(["tesseract", str(png), "-", "--psm", "11"]).stdout
        words = " ".join(re.findall(r"[A-Za-z]+", txt))
        ratio = max((difflib.SequenceMatcher(None, t["text"].lower(), words.lower()[i:i + len(t["text"]) + 4]).ratio()
                     for i in range(max(1, len(words) - len(t["text"]) + 1))), default=0)
        rows.append({"title": t["text"], "t": mid, "ocr_match": round(ratio, 2)})
        png.unlink(missing_ok=True)
    return rows


report = {}
for tag, path in renders.items():
    if not path.exists():
        report[tag] = {"error": "no output"}
        continue
    report[tag] = {"probe": probe(path), "loudness": loudness(path), "black_segments": black(path),
                   "transitions": transitions(path), "titles": ocr_titles(path, tag)}

# Side-by-side sheet: row 1 Concat, row 2 existing engine, same instants.
W, H = 216, 384
sheet = Image.new("RGB", (W * len(SHEET_T), H * 2 + 30), "white")
d = ImageDraw.Draw(sheet)
for r, (tag, path) in enumerate(renders.items()):
    if not path.exists():
        continue
    for k, t in enumerate(SHEET_T):
        f = Image.fromarray(grab(path, t, 216).astype(np.uint8)).resize((W, H))
        sheet.paste(f, (k * W, 30 + r * H))
        d.text((k * W + 4, 32 + r * H), f"{tag} {t}s", fill="red")
for k, t in enumerate(SHEET_T):
    d.text((k * W + 4, 8), f"t={t}s", fill="black")
sheet.save(out / "compare_sheet.png")
(out / "compare.json").write_text(json.dumps(report, indent=1))
print(json.dumps(report, indent=1)[:6000])
