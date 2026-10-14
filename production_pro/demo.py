"""End-to-end real Chromium demo; never publishes or uploads anything."""
from __future__ import annotations
import contextlib, functools, http.server, json, subprocess, threading
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from .recorder import WorkflowRecorder
from .narration import PiperNarrator, EngineeringEspeakNarrator
from .editing import compose_scenes,burn_captions
from .captions import write_captions
from .qc import run_qc
from .models import EditPlan
from production.audio import normalize
SITE=Path(__file__).parent/'site'
NARRATION=[
 'Here is FlowDesk, an original local demonstration. This is not a commercial SaaS product.',
 'We enter a travel expense of one hundred twenty dollars. The app applies its approval threshold and explains the result.',
 'Above one hundred dollars, the actual rule routes this request for manager review. No savings claims or external product endorsements are being made.',
 'A genuine browser recording and simple decision logic. Next, we can build a real business automation step by step.'
]
class _Handler(http.server.SimpleHTTPRequestHandler):
 def __init__(self,*a,**kw): super().__init__(*a,directory=str(SITE),**kw)
 def log_message(self,*a):pass

def _steps():
 def first(p):p.wait_for_timeout(1400)
 def second(p):
  p.locator('#amount').fill('120');p.wait_for_timeout(1100)
 def third(p):
  p.locator('#category').select_option('travel');p.wait_for_timeout(1000)
 def fourth(p):
  p.locator('#submit').click();p.locator('#result').wait_for(state='visible');assert 'MANAGER REVIEW' in p.locator('#result').inner_text();p.wait_for_timeout(1500)
 return [('Open actual demo app',first),('Enter 120 dollars',second),('Select Travel',third),('Apply actual rule',fourth)]

def _card(path:Path,header:str,title:str,subtitle:str,size:tuple[int,int]):
 w,h=size;im=Image.new('RGB',size,(13,20,38));d=ImageDraw.Draw(im)
 try:
  font='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
  ft=ImageFont.truetype(font,55 if w>=1280 else 35);sm=ImageFont.truetype(font,24 if w>=1280 else 17)
 except OSError:ft=ImageFont.load_default();sm=ft
 d.rounded_rectangle((w*.08,h*.13,w*.92,h*.86),radius=32,fill=(23,35,59),outline=(65,99,125),width=3)
 d.text((w*.14,h*.31),header,font=sm,fill=(110,229,194))
 d.text((w*.14,h*.44),title,font=ft,fill=(240,246,255))
 d.text((w*.14,h*.61),subtitle,font=sm,fill=(165,184,215))
 d.text((w*.14,h*.18),'ORIGINAL LOCAL SOFTWARE DEMO · NO EXTERNAL SaaS',font=sm,fill=(116,142,166))
 path.parent.mkdir(parents=True,exist_ok=True);im.save(path)

def _concat_narration(paths:list[Path],out:Path):
 list_file=out.parent/'audio_files.txt';list_file.write_text(''.join("file '"+str(p.resolve())+"'\n" for p in paths))
 proc=subprocess.run(['ffmpeg','-y','-hide_banner','-loglevel','error','-f','concat','-safe','0','-i',str(list_file),'-c:a','pcm_s16le','-ar','48000',str(out)],capture_output=True,text=True)
 if proc.returncode:raise RuntimeError(proc.stderr[-500:])

def run_demo(output_dir:Path,final_output:Path,*,piper_model:Path|None=None,engineering_voice:bool=False,size=(1280,720))->dict:
 output_dir=Path(output_dir);output_dir.mkdir(parents=True,exist_ok=True)
 recording=WorkflowRecorder('local-inline-demo',output_dir/'recording',viewport=size).record(_steps())
 narrator=EngineeringEspeakNarrator() if engineering_voice else PiperNarrator(piper_model)
 narration=narrator.synthesize_segments(NARRATION,output_dir/'narration')
 audio_raw=output_dir/'voice_raw.wav';audio_norm=output_dir/'voice_norm.wav'
 _concat_narration([Path(s.audio_path) for s in narration.segments],audio_raw)
 normalize(audio_raw,audio_norm)
 intro=output_dir/'intro.png';ending=output_dir/'outro.png'
 _card(intro,'REAL SOFTWARE WORKFLOW','Expense approval rules','A functioning original web app, recorded with Playwright',size)
 _card(ending,'REAL DECISION · $120 TRAVEL','Manager review required','This is a working rule, not a performance statistic.',size)
 trans=.35; d1=max(3.5,narration.segments[0].duration_s);d3=max(4.,narration.segments[-1].duration_s)
 mid=max(5.,narration.total_duration_s-d1-d3+2*trans)
 plans=[EditPlan(scene_index=0,source_path=str(intro),duration_s=d1),
  EditPlan(scene_index=1,source_path=recording.video_path,duration_s=mid,transition='smoothleft',overlap_s=trans,highlight_rect=([794,301,417,379] if size[0]==1280 else [1100,300,745,450])),
  EditPlan(scene_index=2,source_path=str(ending),duration_s=d3,transition='fade',overlap_s=trans)]
 composed=output_dir/'composed.mp4'
 edit=compose_scenes(plans,audio_norm,composed,width=size[0],height=size[1],fps=24,workdir=output_dir/'editing')
 captions=output_dir/'captions.ass';count,est_coverage,real=write_captions(narration,captions,size[0],size[1]);assert not real
 burn_captions(composed,captions,final_output)
 qc=run_qc(final_output,captions)
 report={'video':str(final_output.resolve()),'recording':recording.model_dump(),'narrator':narration.backend,'captions':count,'caption_alignment':'approximate','edit':edit,'qc':qc.model_dump(),'publishing':'disabled'}
 (output_dir/'REPORT.json').write_text(json.dumps(report,indent=2))
 return report
