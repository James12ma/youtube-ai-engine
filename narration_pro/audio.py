"""FFmpeg two-pass EBU R128 normalization, with post-render validation."""
from __future__ import annotations
import json,math,re,subprocess
from pathlib import Path
from pydantic import BaseModel

class LoudnessReport(BaseModel):
    input_lufs: float
    input_true_peak: float
    input_lra: float
    target_lufs: float
    output_lufs: float
    output_true_peak: float
    gain_applied_lu: float

_BLOCK=re.compile(r'\{[^{}]*"input_i"[^{}]*\}',re.S)

def _measure(path:Path):
    proc=subprocess.run(["ffmpeg","-hide_banner","-nostats","-i",str(path),
        "-af","loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json","-f","null","-"],capture_output=True,text=True)
    match=_BLOCK.search(proc.stderr)
    if proc.returncode or not match: raise RuntimeError("loudnorm analysis failed")
    data=json.loads(match.group(0))
    for name in ("input_i","input_tp","input_lra","input_thresh","target_offset"):
        if name not in data: raise RuntimeError("loudnorm analysis missing "+name)
        if not math.isfinite(float(data[name])): raise RuntimeError("nonfinite loudness; cannot normalize silence")
    return data

def normalize_loudness(input_path:Path,output_path:Path,*,target_lufs=-16.0,true_peak=-1.5,lra=11.0)->LoudnessReport:
    first=_measure(Path(input_path))
    args=f'loudnorm=I={target_lufs}:TP={true_peak}:LRA={lra}:measured_I={first["input_i"]}:measured_TP={first["input_tp"]}:measured_LRA={first["input_lra"]}:measured_thresh={first["input_thresh"]}:offset={first["target_offset"]}:linear=true:print_format=summary'
    output_path.parent.mkdir(parents=True,exist_ok=True)
    proc=subprocess.run(["ffmpeg","-y","-hide_banner","-loglevel","error","-i",str(input_path),"-af",args,
                         "-ar","48000",str(output_path)],capture_output=True,text=True)
    if proc.returncode: raise RuntimeError("normalization failed: "+proc.stderr[-300:])
    after=_measure(output_path)
    out_i=float(after["input_i"]);out_tp=float(after["input_tp"])
    if abs(out_i-target_lufs)>1.5 or out_tp > true_peak+0.3:
        raise RuntimeError(f"normalized audio outside target: {out_i:.2f} LUFS, {out_tp:.2f} dBTP")
    return LoudnessReport(input_lufs=float(first["input_i"]),input_true_peak=float(first["input_tp"]),
          input_lra=float(first["input_lra"]),target_lufs=target_lufs,
          output_lufs=out_i,output_true_peak=out_tp,gain_applied_lu=out_i-float(first["input_i"]))
