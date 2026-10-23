"""Render the same timeline.json with the EXISTING engine path: production_pro.editing.compose_scenes
(ffmpeg xfade) + adelay/amix/loudnorm audio + animated ASS titles burned with burn_captions."""
import json
import subprocess
import sys
import time
from pathlib import Path

here = Path(__file__).resolve().parent
sys.path.insert(0, str(here.parents[1]))
from production_pro.editing import burn_captions, compose_scenes  # noqa: E402
from production_pro.models import EditPlan  # noqa: E402

out = Path(sys.argv[1]).resolve()
out.mkdir(parents=True, exist_ok=True)
tl = json.loads((here / "timeline.json").read_text())
XF = {"fade": "fade", "slide": "smoothleft", "wipe": "wipeleft"}
t0 = time.time()

plans = []
for k, clip in enumerate(tl["clips"]):
    tr = clip["transition_in"] or {"kind": "fade", "duration_s": 0.0}
    plans.append(EditPlan(scene_index=k, source_path=str(here / clip["source"]), duration_s=clip["duration_s"],
                          transition=XF[tr["kind"]], overlap_s=tr["duration_s"]))

# Audio: narration lines 0.2 s into their clips + music bed, mixed and normalised as the engine does.
n = len(tl["clips"])
inputs, parts = [], []
for i, clip in enumerate(tl["clips"]):
    inputs += ["-i", str(here / f"media/voice{i + 1}.wav")]
    ms = int((clip["start_s"] + 0.2) * 1000)
    parts.append(f"[{i}:a]aresample=48000,aformat=channel_layouts=stereo,adelay={ms}|{ms}[v{i}]")
inputs += ["-i", str(here / tl["music"]["source"])]
parts.append(f"[{n}:a]volume={tl['music']['gain_db']}dB,afade=t=out:st={tl['duration_s'] - 1.5}:d=1.5[m]")
parts.append("".join(f"[v{i}]" for i in range(n)) + f"[m]amix=inputs={n + 1}:normalize=0,apad,atrim=0:{tl['duration_s']},"
             "loudnorm=I=-14:TP=-1.5:LRA=11[a]")
mix = out / "baseline_mix.wav"
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", ";".join(parts), "-map", "[a]",
                "-ar", "48000", str(mix)], check=True)

info = compose_scenes(plans, mix, out / "baseline_notitles.mp4", width=tl["width"], height=tl["height"], fps=tl["fps"],
                      workdir=out / "_edits")


def ts(s):
    return f"{int(s // 3600)}:{int(s % 3600 // 60):02d}:{s % 60:05.2f}"


W, H = tl["width"], tl["height"]
YPOS = {"top": int(H * 0.20), "center": int(H * 0.5), "bottom": int(H * 0.80)}
ass = [f"[Script Info]\nScriptType: v4.00+\nPlayResX: {W}\nPlayResY: {H}\n",
       "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
       "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
       f"Style: T,DejaVu Sans,{int(H * 0.052 * 0.75)},&H00FFFFFF,&H00FFFFFF,&H660C0B0B,&H660C0B0B,1,0,0,0,100,100,0,0,3,18,2,5,40,40,40,1\n",
       "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]
for clip in tl["clips"]:
    t = clip["title"]
    y = YPOS[t["position"]]
    # rise 45 px + scale 86% -> 100% + fade, the same motion the Concat path keys.
    ass.append(f"Dialogue: 0,{ts(t['at_s'])},{ts(t['until_s'])},T,,0,0,0,,"
               f"{{\\fad(350,350)\\move({W // 2},{y + 45},{W // 2},{y},0,490)\\fscx86\\fscy86\\t(0,490,0.5,\\fscx100\\fscy100)}}{t['text']}")
(out / "titles.ass").write_text("\n".join(ass) + "\n")
burn_captions(out / "baseline_notitles.mp4", out / "titles.ass", out / "baseline_15s.mp4")
result = {"ok": (out / "baseline_15s.mp4").exists(), "total_s": round(time.time() - t0, 2), "compose": info}
print(json.dumps(result))
(out / "baseline_result.json").write_text(json.dumps(result, indent=1))
