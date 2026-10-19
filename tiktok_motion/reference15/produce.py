"""15-second original premium editorial motion *reference proof* for YouTube AI Engine.

No downloads, paid APIs, publication, still-image slideshow or use of reference footage.
Run: python -m tiktok_motion.reference15.produce --output /tmp/reference15.mp4
Python stdlib + Pillow + NumPy; requires ffmpeg and ffprobe in PATH.
"""
from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
import tempfile
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS, SECONDS = 720, 1280, 30, 15
BG, WHITE, MUTE = '#080A11', '#F5F3F0', '#9CA2AD'
ORANGE, SOFT, DARK = '#FF702C', '#FEC292', '#171C27'
FONT_DIR = Path('/usr/share/fonts/opentype/inter')


def ease(x: float) -> float:
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def entrance(t: float, start: float, duration: float = .42) -> float:
    return ease((t - start) / duration)


def exit_after(t: float, end: float, duration: float = .48) -> float:
    return 1.0 - ease((t - end) / duration)


def alpha(t: float, start: float, end: float) -> float:
    return entrance(t, start) * exit_after(t, end)


def font(size: int, bold: bool = False):
    name = 'InterDisplay-Bold.otf' if bold else 'InterDisplay-Regular.otf'
    fallback = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    return ImageFont.truetype(str(FONT_DIR / name if (FONT_DIR / name).exists() else fallback), size)


def rgba(code, opacity=255):
    c = code.lstrip('#')
    return tuple(int(c[i:i+2], 16) for i in (0, 2, 4)) + (max(0, min(255, int(opacity))),)


def label(layer, xy, txt, size=20, color=WHITE, bold=False, opacity=255, spacing=0):
    d = ImageDraw.Draw(layer, 'RGBA')
    f = font(size, bold)
    x, y = xy
    if spacing <= 0:
        d.text((int(x), int(y)), txt, font=f, fill=rgba(color, opacity), stroke_width=0)
        return
    for char in txt:
        d.text((int(x), int(y)), char, font=f, fill=rgba(color, opacity))
        x += d.textlength(char, font=f) + spacing


def rect(layer, box, fill, outline=None, radius=15, width=1, opacity=255):
    d = ImageDraw.Draw(layer, 'RGBA')
    x1, y1, x2, y2 = (int(v) for v in box)
    if x2 <= x1 or y2 <= y1:
        return
    d.rounded_rectangle((x1, y1, x2, y2), radius=radius,
                        fill=rgba(fill, opacity) if fill else None,
                        outline=rgba(outline, opacity) if outline else None, width=width)


def line(layer, coords, color, width=2, opacity=255):
    ImageDraw.Draw(layer, 'RGBA').line(tuple(int(v) for v in coords), fill=rgba(color, opacity), width=width, joint='curve')


def base_background():
    yy, xx = np.mgrid[0:H, 0:W]
    radial = np.clip(1-np.sqrt(((xx-W*.53)/(W*.90))**2 + ((yy-H*.48)/(H*.78))**2), 0, 1)
    upper_glow = np.exp(-(((xx-W*.71)/330)**2 + ((yy-H*.37)/540)**2))
    arr = np.empty((H,W,3), dtype=np.uint8)
    for c, val in enumerate((8, 10, 17)):
        arr[:,:,c] = np.clip(val + radial*(c+2)*2 + upper_glow*(9 if c==0 else 2), 0, 255)
    im = Image.fromarray(arr, mode='RGB').convert('RGBA')
    d=ImageDraw.Draw(im,'RGBA')
    for x in range(24,W,38):
        d.line((x,0,x,H), fill=(140,150,175,12),width=1)
    for y in range(20,H,38):
        d.line((0,y,W,y), fill=(140,150,175,12),width=1)
    for y in range(18,H,38):
        for x in range(24,W,38):
            d.ellipse((x-1,y-1,x+1,y+1),fill=(140,150,175,21))
    return im


BACKGROUND = None


def opacity_overlay(canvas, layer, value):
    if value <= 0.001:
        return
    if value < .999:
        r,g,b,a=layer.split()
        a=a.point(lambda v: int(v*value))
        layer.putalpha(a)
    canvas.alpha_composite(layer)


def particle_overlay(canvas, t):
    l=Image.new('RGBA',(W,H)); d=ImageDraw.Draw(l,'RGBA')
    for idx in range(26):
        x = 22 + ((idx*181 + t*(12+idx%5*4)) % (W-44))
        y = 160 + ((idx*197 + t*(14+idx%4*6)) % 1010)
        r = .7+idx%3*.4
        d.ellipse((x-r,y-r,x+r,y+r), fill=(255,133,77,20 + idx%4*5))
    canvas.alpha_composite(l)


def chrome(canvas,t,scene):
    l=Image.new('RGBA',(W,H))
    rect(l,(37,48,185,83),ORANGE,radius=6)
    label(l,(48,54),'LOGICSCRIPT',16,BG,True,spacing=1)
    label(l,(207,56),'MOTION LAB / 001',15,MUTE,spacing=2)
    label(l,(589,56),f'{int(t):02d}:{int(t%1*FPS):02d}',15,MUTE,True)
    line(l,(37,102,683,102),'#343947',1,130)
    line(l,(37,1160,683,1160),'#303642',1,130)
    label(l,(37,1186),'EDITORIAL MOTION STUDY',14,MUTE,False,spacing=1)
    label(l,(601,1186),'15 SEC',15,ORANGE,True)
    # timeline ticks + active segment
    for i in range(31):
        x=42+i*21
        line(l,(x,1135,x,1142 if i%5 else 1148),'#525D6C',1,90)
    x=42+min(30,t/15*30)*21
    rect(l,(42,1129,x,1132),ORANGE,radius=2)
    # A small always-live visual meter prevents static hold frames. The bar heights
    # are procedural, deterministic and signal activity rather than real AI data.
    label(l,(76,923),'LIVE MOTION  /  SIGNAL FLOW',13,MUTE,True,spacing=1)
    for idx in range(44):
        x=78+idx*13
        energy=.5+.5*math.sin(t*4.7 + idx*.55)
        slower=.5+.5*math.sin(t*2.1 - idx*.29)
        hh=int(16+34*energy+12*slower)
        rect(l,(x,1019-hh,x+6,1019),ORANGE if idx%9==0 else '#667387',radius=2,
             opacity=int(60 + 170*energy))
    # Sliding trace shows tempo and supplies continuous purposeful 2D motion.
    x=78+int((t*.65%1)*561)
    rect(l,(max(76,x-14),1026,min(654,x+14),1030),ORANGE,radius=2)
    # Scene navigation appears as a persistent motif, not a hard cut.
    for j,text in enumerate(('PROMPT','PREDICT','OUTPUT')):
        ox=76+j*214
        lab_col = ORANGE if j==scene else MUTE
        line(l,(ox,1085,ox+162,1085),lab_col,3 if j==scene else 1,255 if j==scene else 75)
        label(l,(ox,1055),f'0{j+1}  {text}',14,lab_col,j==scene)
    canvas.alpha_composite(l)


def heading(canvas,t):
    l=Image.new('RGBA',(W,H))
    visibility=alpha(t,.12,12.8)
    dy=round((1-entrance(t,.20,.72))*22)
    label(l,(76,153+dy),'THE 15-SECOND BREAKDOWN',16,MUTE,False,spacing=2)
    label(l,(72,202+dy),'HOW AI CHOOSES',47,WHITE,True)
    label(l,(72,267+dy),'THE NEXT WORD',59,ORANGE,True)
    line(l,(74,350,74+int(546*entrance(t,.4,.85)),350),ORANGE,3)
    opacity_overlay(canvas,l,visibility)


def header_bar(l, x, y, w, txt):
    rect(l,(x,y,x+w,y+44),'#121723',outline='#313A4B',radius=9,width=2)
    for i,c in enumerate(('#FF794B','#FAB55C','#6FBF9F')):
        ImageDraw.Draw(l,'RGBA').ellipse((x+15+i*18,y+16,x+24+i*18,y+25),fill=rgba(c))
    label(l,(x+105,y+11),txt,15,MUTE,True,spacing=1)


def type_prompt(l, t, y, full='The sky is ...'):
    typed = int(len(full) * entrance(t, .8, 2.05))
    txt = full[:typed]
    label(l,(105,y),txt,36,WHITE,True)
    if int(t*2.8)%2==0:
        ww=ImageDraw.Draw(l).textlength(txt,font=font(36,True))
        rect(l,(109+ww,y+5,114+ww,y+41),ORANGE,radius=1)


def prompt_scene(canvas,t):
    v=alpha(t,.55,4.45)
    if not v:return
    l=Image.new('RGBA',(W,H))
    y_shift=round((1-entrance(t,.52,.55))*55)
    x1,y1,x2,y2=66,430+y_shift,654,865+y_shift
    rect(l,(x1+9,y1+13,x2+9,y2+13),'#000000',radius=22,opacity=135)
    rect(l,(x1,y1,x2,y2),'#111622',outline='#3F4658',radius=22,width=2)
    header_bar(l,x1+19,y1+19,550,'USER INPUT / TOKENIZER')
    label(l,(104,y1+106),'The prompt',20,MUTE,False)
    type_prompt(l,t,y1+157)
    line(l,(105,y1+226,612,y1+226),'#3D4655',2)
    label(l,(104,y1+272),'INPUT TOKENS',16,MUTE,True,spacing=2)
    for i,(txt,st) in enumerate((('The',1.45),('sky',1.76),('is',2.06),('...',2.38))):
        p=entrance(t,st,.28)
        px=106+i*126; py=y1+326+int((1-p)*22)
        rect(l,(px,py,px+105,py+51),'#242A39',outline=ORANGE if i==3 else '#474D5D',radius=10,opacity=round(p*255))
        label(l,(px+21,py+8),txt,23,ORANGE if i==3 else WHITE,True,opacity=round(p*255))
    opacity_overlay(canvas,l,v)


def predict_scene(canvas,t):
    v=alpha(t,4.05,9.43)
    if not v:return
    l=Image.new('RGBA',(W,H))
    shift=round((1-entrance(t,4.1,.55))*55)
    x1,y1,x2,y2=65,423+shift,654,947+shift
    rect(l,(x1+8,y1+12,x2+8,y2+12),'#000000',radius=20,opacity=150)
    rect(l,(x1,y1,x2,y2),'#111622',outline='#41495A',radius=20,width=2)
    header_bar(l,x1+19,y1+19,552,'PREDICTION ENGINE')
    label(l,(102,y1+91),'The sky is',31,WHITE,True)
    rect(l,(320,y1+90,427,y1+136),'#2F251F',outline=ORANGE,radius=8,width=2)
    label(l,(338,y1+96),'[ ? ]',26,ORANGE,True)
    label(l,(100,y1+171),'NEXT-TOKEN SCORES',15,MUTE,True,spacing=2)
    scores=[('blue',72,ORANGE),('clear',19,'#798BAE'),('dark',9,'#657188')]
    for j,(name,score,col) in enumerate(scores):
        p=entrance(t,4.80+j*.32,.76)
        yy=y1+221+j*93
        label(l,(102,yy),name.upper(),19,WHITE,j==0,opacity=round(p*255))
        label(l,(539,yy),f'{score}%',21,col,True,opacity=round(p*255))
        rect(l,(102,yy+39,604,yy+55),'#273040',radius=6,opacity=round(p*220))
        if p>0.01:
            rect(l,(102,yy+39,102+int(502*score/100*p),yy+55),col,radius=6,opacity=round(255*p))
    line(l,(103,y1+493,602,y1+493),'#485062',1,125)
    label(l,(104,y1+505),'SCHEMATIC EXAMPLE • NOT MODEL MEASUREMENTS',12,MUTE)
    # live pulsing selected indicator
    pulse=(math.sin(t*7)+1)*.5
    rect(l,(90,y1+208,95,y1+284),ORANGE,radius=2,opacity=160+round(pulse*95))
    opacity_overlay(canvas,l,v)


def output_scene(canvas,t):
    v=alpha(t,9.05,12.78)
    if not v:return
    l=Image.new('RGBA',(W,H))
    shift=round((1-entrance(t,9.12,.5))*55)
    x1,y1,x2,y2=66,428+shift,654,903+shift
    rect(l,(x1+8,y1+12,x2+8,y2+12),'#000000',radius=20,opacity=145)
    rect(l,(x1,y1,x2,y2),'#111622',outline='#424A5B',radius=20,width=2)
    header_bar(l,85,y1+19,550,'GENERATED OUTPUT')
    label(l,(105,y1+107),'NEXT TOKEN SELECTED',17,MUTE,True,spacing=1)
    rect(l,(105,y1+156,601,y1+237),'#1B2332',outline='#42516A',radius=13,width=2)
    label(l,(124,y1+165),'The sky is',31,WHITE,True)
    p=entrance(t,9.55,1.2)
    rect(l,(380,y1+164,380+int(115*p),y1+219),'#42261B',outline=ORANGE,radius=9,opacity=round(p*255))
    label(l,(391,y1+170),'blue',29,ORANGE,True,opacity=round(p*255))
    if p>.7:
        label(l,(505,y1+166),'.',35,WHITE,True,opacity=round((p-.7)/.3*255))
    for j,tx in enumerate(('1. TOKENIZE','2. SCORE','3. SELECT')):
        x=108+j*166; yy=y1+312
        a=entrance(t,9.5+j*.38,.45)
        rect(l,(x,yy,x+148,yy+60),'#283041' if j!=2 else '#3B291F',outline=ORANGE if j==2 else '#485263',radius=9,opacity=round(a*255))
        label(l,(x+12,yy+18),tx,14,ORANGE if j==2 else WHITE,True,opacity=round(a*255))
        if j<2:
            line(l,(x+148,yy+30,x+165,yy+30),ORANGE,2,opacity=round(a*255))
    opacity_overlay(canvas,l,v)


def end_scene(canvas,t):
    v=entrance(t,12.65,.48)
    if not v:return
    l=Image.new('RGBA',(W,H))
    dy=round((1-v)*50)
    label(l,(74,460+dy),'ONE TOKEN',66,WHITE,True,opacity=round(v*255))
    label(l,(74,547+dy),'AT A TIME.',68,ORANGE,True,opacity=round(v*255))
    # animated progress marks deliberately make this a moving scene.
    for j in range(12):
        x=75+j*49
        p=entrance(t,13.13+j*.085,.38)
        rect(l,(x,700,x+27,700+int(10+42*p)),ORANGE if j<8 else '#3F4553',radius=5,opacity=round(p*255))
    label(l,(76,791),'ILLUSTRATED CONCEPT  /  NOT LIVE MODEL DATA',17,MUTE,False,opacity=round(v*255))
    line(l,(76,835,76+int(565*v),835),ORANGE,2)
    opacity_overlay(canvas,l,v)


def frame(t: float):
    global BACKGROUND
    if BACKGROUND is None:BACKGROUND=base_background()
    im=BACKGROUND.copy()
    particle_overlay(im,t)
    heading(im,t)
    prompt_scene(im,t)
    predict_scene(im,t)
    output_scene(im,t)
    end_scene(im,t)
    scene=0 if t<4.7 else (1 if t<9.7 else 2)
    chrome(im,t,scene)
    return im.convert('RGB')


def wav_sound(path: Path, seconds=SECONDS, sample_rate=44100):
    """Original generated underscore, beats, taps and scene changes; no third-party samples."""
    n=int(seconds*sample_rate)
    t=np.arange(n,dtype=np.float32)/sample_rate
    out=np.zeros(n,dtype=np.float32)
    # Gentle underscore: layered tone with envelope and low-frequency rhythm.
    fade=np.minimum(np.minimum(t/1.0,(seconds-t)/1.0),1).clip(0,1)
    out += .045*np.sin(2*np.pi*110*t)*fade
    out += .022*np.sin(2*np.pi*165*t + .23*np.sin(2*np.pi*.37*t))*fade
    for beat in np.arange(.5,seconds-.4,.5):
        o=t-beat
        env=np.exp(-17*np.maximum(o,0))*(o>=0)
        out+=.032*env*np.sin(2*np.pi*230*o)
    for beat in (0.45,4.25,9.20,12.80):
        o=t-beat
        idx=(o>=0)&(o<.42)
        # Noise sweeps with a smooth decay, deterministic, original.
        rng=np.random.default_rng(int(beat*1000))
        noise=rng.normal(0,1,int(idx.sum())).astype(np.float32)
        out[idx]+=.06*noise*np.sin(np.pi*o[idx]/.42)**1.3
        out[idx]+=.055*np.exp(-o[idx]*13)*np.sin(2*np.pi*(320-200*o[idx])*o[idx])
    out=np.tanh(out*1.5)*.70
    pcm=(out*32767).clip(-32768,32767).astype('<i2')
    with wave.open(str(path),'wb') as wf:
        wf.setnchannels(1);wf.setsampwidth(2);wf.setframerate(sample_rate);wf.writeframes(pcm.tobytes())


def produce(output: Path, preview=False):
    if not shutil.which('ffmpeg') or not shutil.which('ffprobe'):
        raise RuntimeError('ffmpeg and ffprobe are required; no online downloads')
    output=output.resolve();output.parent.mkdir(parents=True,exist_ok=True)
    dur=3 if preview else SECONDS
    with tempfile.TemporaryDirectory(prefix='logicscript-ref15-') as tmp:
        audio=Path(tmp)/'original_score.wav';wav_sound(audio,seconds=dur)
        cmd=['ffmpeg','-hide_banner','-loglevel','error','-y','-f','rawvideo','-pix_fmt','rgb24',
             '-s',f'{W}x{H}','-r',str(FPS),'-i','pipe:0','-i',str(audio),
             '-vf','scale=1080:1920:flags=lanczos,format=yuv420p',
             '-c:v','libx264','-preset','veryfast','-crf','19','-r',str(FPS),
             '-c:a','aac','-b:a','160k','-t',str(dur),'-movflags','+faststart',str(output)]
        proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
        try:
            for j in range(FPS*dur):
                proc.stdin.write(frame(j/FPS).tobytes())
            proc.stdin.close();err=proc.stderr.read();result=proc.wait()
        except BaseException:
            proc.kill();proc.wait();raise
        if result!=0: raise RuntimeError(f'ffmpeg render failed: {err.decode(errors="replace")[:1000]}')
    scan=subprocess.run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(output)],capture_output=True,text=True,check=True)
    probe=json.loads(scan.stdout); vid=next(s for s in probe['streams'] if s['codec_type']=='video')
    audio_ok=any(s['codec_type']=='audio' for s in probe['streams'])
    runtime=float(probe['format']['duration'])
    status=vid['width']==1080 and vid['height']==1920 and vid['codec_name']=='h264' and abs(runtime-dur)<.12 and audio_ok
    report={'type':'original_procedural_15s_reference','duration_seconds':runtime,'resolution':'1080x1920','fps':FPS,
            'video_codec':vid['codec_name'],'audio_present':audio_ok,'audio_type':'original_synth_score_no_narration',
            'content':'token-prediction concept; numbers illustrative, not measured',
            'is_reusable_general_topic_engine':False,'source_pipeline':'tiktok_motion.reference15.produce',
            'reference_footage_included':False,'paid_services_used':False,'uploaded':False,
            'requires_owner_approval':True,'auto_publish':False,'render_status':'passed' if status else 'failed'}
    report_path=output.with_suffix('.engine_run.json');report_path.write_text(json.dumps(report,indent=2))
    if not status:raise RuntimeError(f'Technical QA failed: {report_path}')
    return report


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True)
    p.add_argument('--preview',action='store_true')
    args=p.parse_args();print(json.dumps(produce(args.output,args.preview),indent=2))


if __name__=='__main__':main()
