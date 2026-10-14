from __future__ import annotations
import subprocess
from pathlib import Path
from .errors import RenderError

def make_clip(img:Path,out:Path,duration:float,width:int,height:int,fps:int,crf:int,preset:str,temp_scale:int=1):
    if duration<=0: raise RenderError('non-positive scene duration')
    # d=1 ensures exactly one zoompan frame per input frame; avoids 30x work.
    # Default no massive 4x input upscaling (can exceed free runner memory).
    frames=max(1,round(duration*fps));scale=max(1,min(int(temp_scale),2))
    w=width*scale;h=height*scale
    vf=f"scale={w}:{h}:flags=lanczos,zoompan=z='min(1.06,1+0.06*on/{frames})':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={width}x{height}:fps={fps},format=yuv420p"
    cmd=['ffmpeg','-y','-hide_banner','-loglevel','error','-loop','1','-framerate',str(fps),'-i',str(img),'-vf',vf,'-frames:v',str(frames),'-c:v','libx264','-threads','2','-preset',preset,'-crf',str(crf),'-pix_fmt','yuv420p','-an',str(out)]
    p=subprocess.run(cmd,capture_output=True,text=True,timeout=120)
    if p.returncode: raise RenderError('scene rendering failed: '+p.stderr[-700:])
    return out
