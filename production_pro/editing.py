"""Actual FFmpeg trims, still-card looping, transitions, focus zooms, and highlights."""
from __future__ import annotations
import json,subprocess
from pathlib import Path
from fractions import Fraction
from .models import EditPlan
from .errors import EditingError

TRANSITIONS={'fade','smoothleft','wipeleft'}

def _run(cmd):
 proc=subprocess.run(cmd,capture_output=True,text=True)
 if proc.returncode:raise EditingError(proc.stderr[-1200:])

def _probe(path):
 proc=subprocess.run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(path)],check=True,capture_output=True,text=True)
 return json.loads(proc.stdout)

def _source_clip(plan:EditPlan,dest:Path,width:int,height:int,fps:int):
 src=Path(plan.source_path)
 if not src.exists():raise EditingError(f'missing source: {src}')
 still=src.suffix.lower() in ('.png','.jpg','.jpeg')
 if still and plan.photo_motion:
  # Fill the frame (no letterbox) and zoom slowly towards the centre.
  frames=max(2,int(round(plan.duration_s*fps)))
  w2,h2=width*2,height*2
  vf=(f'scale={w2}:{h2}:force_original_aspect_ratio=increase,crop={w2}:{h2},'
      f"zoompan=z='1+0.10*on/{frames}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={width}x{height}:fps={fps},"
      f'setsar=1,settb=AVTB,format=yuv420p')
  _run(['ffmpeg','-y','-hide_banner','-loglevel','error','-i',str(src),'-vf',vf,'-t',f'{plan.duration_s:.3f}',
        '-an','-c:v','libx264','-preset','veryfast','-crf','21','-pix_fmt','yuv420p',str(dest)])
  return float(_probe(dest)['format']['duration'])
 cmd=['ffmpeg','-y','-hide_banner','-loglevel','error']
 if still:cmd+=['-loop','1','-framerate',str(fps),'-i',str(src)]
 else:cmd+=['-ss',str(plan.start_s),'-i',str(src)]
 scale=f'scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=0x101420'
 if plan.zoom>1.001:
  cw=int(width/plan.zoom)//2*2;ch=int(height/plan.zoom)//2*2
  scale+=f',crop={cw}:{ch}:(iw-{cw})/2:(ih-{ch})/2,scale={width}:{height}:flags=lanczos'
 if plan.highlight_rect:
  x,y,w,h=plan.highlight_rect
  if min(x,y,w,h)<0 or x+w>width or y+h>height or w<1 or h<1:raise EditingError('highlight outside source dimensions')
  scale+=f',drawbox=x={x}:y={y}:w={w}:h={h}:color=0x70e7c4@0.85:t=6'
 vf=scale+f',fps={fps},setsar=1,settb=AVTB,format=yuv420p,tpad=stop_mode=clone:stop_duration={plan.duration_s:.3f}'
 cmd+=['-vf',vf,'-t',str(plan.duration_s),'-an','-c:v','libx264','-preset','veryfast','-crf','21','-pix_fmt','yuv420p',str(dest)]
 _run(cmd)
 return float(_probe(dest)['format']['duration'])

def compose_scenes(plans:list[EditPlan],audio_path:Path,output:Path,*,width=1280,height=720,fps=24,workdir:Path|None=None)->dict:
 if not plans:raise EditingError('no plans')
 if any(plan.transition not in TRANSITIONS for plan in plans):raise EditingError('unsupported transition')
 workdir=workdir or output.parent/'_edits';workdir.mkdir(parents=True,exist_ok=True)
 normalized=[];durations=[]
 for i,plan in enumerate(plans):
  path=workdir/f'norm_{i}.mp4';durations.append(_source_clip(plan,path,width,height,fps));normalized.append(path)
 inputs=[]
 for path in normalized:inputs+=['-i',str(path)]
 filters=[];prior='0:v';total=durations[0]
 for i in range(1,len(plans)):
  overlap=min(plans[i].overlap_s,0.4*durations[i],0.4*total)
  offset=total-overlap
  name=f'mix{i}'
  filters.append(f'[{prior}][{i}:v]xfade=transition={plans[i].transition}:duration={overlap:.3f}:offset={offset:.3f}[{name}]')
  prior=name;total=total+durations[i]-overlap
 chained=workdir/'chained.mp4'
 if not filters:
  _run(['ffmpeg','-y','-hide_banner','-loglevel','error','-i',str(normalized[0]),'-an','-c:v','copy',str(chained)])
 else:
  _run(['ffmpeg','-y','-hide_banner','-loglevel','error',*inputs,'-filter_complex',';'.join(filters),'-map',f'[{prior}]','-c:v','libx264','-preset','veryfast','-crf','21','-pix_fmt','yuv420p',str(chained)])
 output.parent.mkdir(parents=True,exist_ok=True)
 _run(['ffmpeg','-y','-hide_banner','-loglevel','error','-i',str(chained),'-i',str(audio_path),'-c:v','copy','-c:a','aac','-b:a','192k','-movflags','+faststart','-shortest',str(output)])
 p=_probe(output)
 return {'duration_s':float(p['format']['duration']),'width':width,'height':height,'fps':fps,'scene_count':len(plans),'video_codec':'h264','audio_codec':'aac'}

def burn_captions(video_path:Path,ass_path:Path,output:Path):
 # POSIX path filtering: workdir with no colons/quotes; ffmpeg subtitles needs safe filename escaping.
 sub=str(ass_path.resolve()).replace('\\','\\\\').replace(':','\\:').replace("'",r"\'").replace('[',r'\[').replace(']',r'\]')
 _run(['ffmpeg','-y','-hide_banner','-loglevel','error','-i',str(video_path),'-vf',"subtitles=filename='"+sub+"'",'-c:v','libx264','-preset','veryfast','-crf','20','-c:a','copy','-movflags','+faststart',str(output)])
