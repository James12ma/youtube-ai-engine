from __future__ import annotations
import json,re,subprocess
from pathlib import Path
from .errors import RenderError

def loudness(path: Path,target=-16.0,tp=-1.5,lra=11.0):
    cmd=['ffmpeg','-hide_banner','-nostats','-i',str(path),'-af',f'loudnorm=I={target}:TP={tp}:LRA={lra}:print_format=json','-f','null','-']
    p=subprocess.run(cmd,capture_output=True,text=True)
    if p.returncode: raise RenderError('measure loudness failed: '+p.stderr[-350:])
    match=re.search(r'\{[^{}]*"input_i"[^{}]*\}',p.stderr,re.S)
    if match is None: raise RenderError('loudnorm JSON missing')
    return json.loads(match.group(0))

def normalize(input_path:Path,output_path:Path,target=-16,tp=-1.5,lra=11.):
    m=loudness(input_path,target,tp,lra)
    parts=[f'loudnorm=I={target}',f'TP={tp}',f'LRA={lra}',f'measured_I={m["input_i"]}',f'measured_TP={m["input_tp"]}',f'measured_LRA={m["input_lra"]}',f'measured_thresh={m["input_thresh"]}',f'offset={m["target_offset"]}', 'linear=true','print_format=summary']
    # filter options MUST use colons, not commas (which separate filters).
    p=subprocess.run(['ffmpeg','-y','-hide_banner','-loglevel','error','-i',str(input_path),'-af',':'.join(parts),'-ar','48000','-ac','1','-c:a','pcm_s16le',str(output_path)],capture_output=True,text=True)
    if p.returncode: raise RenderError('normalize failed: '+p.stderr[-600:])

def concat_wavs(inputs:list[Path],output:Path):
    if not inputs: raise RenderError('no audio inputs')
    filelist=output.parent/'audio_inputs.txt'
    # fail on quotes/newlines in path rather than silently generating invalid concat list
    for file in inputs:
        if "'" in str(file) or '\n' in str(file): raise RenderError('unsafe audio path')
    filelist.write_text(''.join(f"file '{p.resolve()}'\n" for p in inputs))
    p=subprocess.run(['ffmpeg','-y','-hide_banner','-loglevel','error','-f','concat','-safe','0','-i',str(filelist),'-ar','48000','-ac','1','-c:a','pcm_s16le',str(output)],capture_output=True,text=True)
    if p.returncode: raise RenderError('concat audio failed: '+p.stderr[-500:])
