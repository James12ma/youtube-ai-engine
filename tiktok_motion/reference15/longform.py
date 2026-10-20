"""98 s original career explainer, built on the approved 15 s YouTube AI Engine visual module.

Standalone continuation of ``tiktok_motion.reference15.produce``. No reference footage,
paid services, network calls, publication or modification of existing channel engines.
Narration uses offline eSpeak engineering voice, plainly not a premium neural voice.
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
from PIL import Image, ImageDraw
from scipy.signal import resample_poly

from .produce import (W,H,BG,WHITE,MUTE,ORANGE,DARK,SOFT,base_background,opacity_overlay,
                      font,label,rect,line,rgba,ease,entrance,alpha)

FPS=30
DURATION=98
TOPIC="5 TYPES OF JOB INTERVIEWS"
ROOT=Path(__file__).resolve().parent
SEGMENTS=[
    (0,10,"THE INTERVIEW PLAYBOOK","5 FORMATS. 5 WAYS TO PREPARE.",
     "Different interviews test different skills. Here are five common formats, and one smart move for each."),
    (10,25,"01 / PHONE INTERVIEW","YOUR VOICE IS THE FIRST IMPRESSION",
     "One. Phone interview. The recruiter hears confidence, not body language. Stand up, smile, and keep a few notes nearby. Speak clearly and leave room for questions."),
    (25,40,"02 / VIDEO INTERVIEW","YOUR CAMERA TELLS A STORY",
     "Two. Video interview. Your camera is part of the first impression. Test the microphone, face soft natural light, and place the lens at eye level."),
    (40,55,"03 / IN-PERSON INTERVIEW","PRESENCE IS PART OF THE ANSWER",
     "Three. In-person interview. Presence counts. Arrive a little early, make natural eye contact, and bring thoughtful questions about the role."),
    (55,70,"04 / PANEL INTERVIEW","ONE ANSWER. MULTIPLE LISTENERS.",
     "Four. Panel interview. You may speak with several interviewers at once. First, answer the person who asked, then include everyone with your eye contact."),
    (70,85,"05 / BEHAVIORAL INTERVIEW","USE THE S.T.A.R. METHOD",
     "Five. Behavioral interview. Expect: tell me about a time. Use S T A R: Situation, Task, Action, Result. Finish with a measurable outcome."),
    (85,98,"THE ONE-MINUTE RECAP","PREPARE. PRACTICE. FOLLOW UP.",
     "The takeaway: prepare one strong example, adapt to the interview format, and send a short thank-you afterward. Save this checklist for your next interview."),
]
CHAPTERS=[(s,e,title) for s,e,title,_,_ in SEGMENTS]
BASE=None

def txt(l,x,y,text,size=23,color=WHITE,bold=False,opacity=255):
    label(l,(x,y),text,size,color,bold,opacity)

def pill(l,x,y,word,accent=False,width=None,opa=255):
    fw=int(ImageDraw.Draw(l).textlength(word,font=font(18,True)))
    w=width or (fw+34)
    rect(l,(x,y,x+w,y+48),'#1B2433' if not accent else '#482C23',outline=ORANGE if accent else '#394558',radius=12,width=2,opacity=opa)
    txt(l,x+17,y+12,word,18,ORANGE if accent else WHITE,True,opa)

def panel(l,box,opacity=255,accent=False):
    x1,y1,x2,y2=box
    rect(l,(x1+9,y1+13,x2+9,y2+13),'#030509',radius=21,opacity=int(opacity*.7))
    rect(l,box,'#111723',outline=ORANGE if accent else '#374355',radius=21,width=2,opacity=opacity)

def circle(l,x,y,r,fill,outline=None,ow=3,opacity=255):
    ImageDraw.Draw(l,'RGBA').ellipse((int(x-r),int(y-r),int(x+r),int(y+r)),fill=rgba(fill,opacity) if fill else None,
                                      outline=rgba(outline,opacity) if outline else None,width=ow)

def scene_bar(l,t,idx,title):
    line(l,(48,100,672,100),'#364052',2,160)
    rect(l,(46,40,178,77),ORANGE,radius=7)
    txt(l,58,48,'LOGICSCRIPT',15,BG,True)
    txt(l,200,48,'MOTION STUDIO   /   CAREER SERIES',15,MUTE,True)
    txt(l,48,123,title,17,MUTE,True)
    rect(l,(48,1185,672,1188),'#354055',radius=2)
    rect(l,(48,1185,48+(624*t/DURATION),1188),ORANGE,radius=2)
    txt(l,48,1206,f'CHAPTER {idx+1:02d} / {len(SEGMENTS):02d}',15,ORANGE,True)
    txt(l,526,1206,f'{int(t//60):02d}:{int(t%60):02d} / 01:38',14,MUTE,True)


def lower_text(l,t,start,end,title,note):
    p=entrance(t,start+.2,.6)
    y=934+int((1-p)*36)
    txt(l,60,y,title,23,WHITE,True,round(255*p))
    # wrap note on word boundaries
    d=ImageDraw.Draw(l)
    words=note.split();lines=[];cur=''
    for word in words:
        trial=(cur+' '+word).strip()
        if d.textlength(trial,font=font(21))>575 and cur:
            lines.append(cur);cur=word
        else:cur=trial
    if cur:lines.append(cur)
    for j,s in enumerate(lines[:3]):
        txt(l,60,y+46+j*34,s,21,MUTE,False,round(255*p))
    line(l,(60,y-22,60+int(565*min(1,(t-start)/1.1)),y-22),ORANGE,3,round(255*p))


def hook(l,t,local):
    a=entrance(t,0,.7)
    txt(l,60,225,'THE INTERVIEW',53,WHITE,True,round(a*255))
    txt(l,60,302,'PLAYBOOK',84,ORANGE,True,round(a*255))
    txt(l,63,414,'5 formats. 5 ways to prepare.',25,MUTE,False,round(a*255))
    # Five depth-staggered connected nodes — purposeful continuous motion
    for i in range(5):
        p=entrance(t,.7+i*.22,.56)
        x=95+i*128
        y=660 + 19*math.sin(2.0*local+i*.65) - (1-p)*115
        circle(l,x,y,32,'#1D2839',ORANGE,3,round(p*255))
        txt(l,x-14,y-17,str(i+1).zfill(2),22,WHITE,True,round(p*255))
        if i<4:line(l,(x+34,y,x+93,y),'#5B6675',3,round(p*180))
    txt(l,77,780,'PHONE  /  VIDEO  /  IN PERSON',22,WHITE,True,round(255*entrance(t,2.0,.7)))
    txt(l,143,821,'PANEL  /  BEHAVIORAL',22,ORANGE,True,round(255*entrance(t,3.2,.7)))
    lower_text(l,t,0,10,'WHAT YOU WILL LEARN','A practical guide to five interview formats.')


def phone(l,t,local):
    p=entrance(t,10.2,.65)
    off=int((1-p)*90)
    # animated telephone frame
    panel(l,(166,280+off,557,861+off),round(255*p))
    rect(l,(203,323+off,522,798+off),'#0D1725',radius=28,opacity=round(255*p))
    txt(l,258,367+off,'INCOMING CALL',18,MUTE,True,round(255*p))
    circle(l,362,484+off,63,'#2E3A4D',ORANGE,4,round(255*p))
    txt(l,319,471+off,'HR',37,WHITE,True,round(255*p))
    txt(l,266,579+off,'Recruiter',32,WHITE,True,round(255*p))
    txt(l,284,626+off,'00:'+str(int((local)%60)).zfill(2),21,MUTE,True,round(255*p))
    circle(l,284,718+off,30,'#D54D51',opacity=round(255*p))
    circle(l,437,718+off,30,'#287A5B',opacity=round(255*p))
    txt(l,267,706+off,'×',34,WHITE,True,round(255*p))
    txt(l,425,700+off,'✓',30,WHITE,True,round(255*p))
    # animated speech waveform and ripple
    for k in range(24):
        x=224+k*12
        hh=8+34*(.5+.5*math.sin(local*6.8+k*.57))
        rect(l,(x,820+off-hh,x+6,820+off),ORANGE if k%3==0 else '#768498',radius=2,opacity=round(230*p))
    for n in range(2):
        r=62+int((local*45+n*37)%74)
        circle(l,362,484+off,r,None,'#FF702C',2,round(45*p*(1-(r-62)/145)))
    pill(l,56,855,'STAND UP',True)
    pill(l,230,855,'SMILE')
    pill(l,362,855,'USE NOTES')
    lower_text(l,t,10,25,'01  PHONE INTERVIEW','Your delivery matters when nobody sees you.')


def video(l,t,local):
    p=entrance(t,25.2,.62)
    panel(l,(62,318,657,790),round(255*p))
    rect(l,(84,353,635,731),'#19263A',radius=15,opacity=round(p*255))
    # abstract participant, not copied photo
    circle(l,345,489+2*math.sin(local*2),74,'#657FA1',opacity=round(255*p))
    rect(l,(222,560,468,721),'#405B7B',radius=95,opacity=round(255*p))
    rect(l,(96,368,208,404),'#15293A',radius=9,opacity=round(255*p))
    txt(l,108,375,'CAM  ON',16,'#A3F0CD',True,round(255*p))
    rect(l,(531,368,619,404),'#15293A',radius=9,opacity=round(255*p))
    txt(l,538,375,'LIVE',17,ORANGE,True,round(255*p))
    # camera tracking markers + faint rings
    for k in range(4):
        ph=(local*.8+k*.25)%1
        rr=82+ph*46
        circle(l,345,489,rr,None,'#97ABC8',2,round((1-ph)*50*p))
    for i in range(6):
        hh=14+33*(.5+.5*math.sin(4*local+i*.7))
        rect(l,(487+i*16,650-hh,496+i*16,650),'#A3F0CD',radius=3,opacity=round(210*p))
    txt(l,109,754,'YOUR VIDEO SETUP',20,WHITE,True,round(255*p))
    for i,(a,b) in enumerate([('LIGHT','FACE A WINDOW'),('AUDIO','TEST YOUR MIC'),('CAMERA','EYE LEVEL')]):
        y=826+i*48
        txt(l,71,y,a,19,ORANGE,True,round(255*p))
        txt(l,222,y,b,20,WHITE,True,round(255*p))
        line(l,(69,y+36,638,y+36),'#3C485C',1,round(110*p))
    lower_text(l,t,25,40,'02  VIDEO INTERVIEW','Look into the lens when you answer.')


def people(l,cx,cy,scale=1,active=False):
    circle(l,cx,cy-54*scale,30*scale,'#8AA0B6' if active else '#5C7087',opacity=240)
    rect(l,(cx-52*scale,cy-21*scale,cx+52*scale,cy+78*scale),'#C0D1DC' if active else '#344B63',radius=int(36*scale))
    if active:circle(l,cx,cy-54*scale,36*scale,None,ORANGE,3)


def inperson(l,t,local):
    p=entrance(t,40.15,.58)
    panel(l,(50,302,670,824),round(255*p))
    # editorial hallway architecture with perspective lines
    for xx in (111,609):
        line(l,(xx,340,xx+(350-xx)*.24,712),'#465369',2,round(145*p))
    line(l,(83,722,628,722),'#5B6779',3,round(170*p))
    for y in (397,477,558):
        line(l,(78,y,632,y),'#293747',1,round(170*p))
    people(l,229,582,1.14,False); people(l,471,582,1.14,True)
    line(l,(277,598,420,598),ORANGE,10,round(p*220))
    # animated handshake pivot
    cx=350+math.sin(local*1.7)*7
    circle(l,cx,597,16,'#F6B48A',opacity=round(255*p))
    txt(l,103,360,'FACE-TO-FACE',21,ORANGE,True,round(255*p))
    for i,(number,heading) in enumerate([('01','ARRIVE EARLY'),('02','MAKE EYE CONTACT'),('03','ASK QUESTIONS')]):
        x=71+i*208; y=853
        pill(l,x,y,number,True,width=60,opa=round(255*entrance(t,41+i*.7,.5)))
        txt(l,x,y+55,heading,17,WHITE,True,round(255*p))
    lower_text(l,t,40,55,'03  IN-PERSON INTERVIEW','Be confident, curious, and prepared.')


def panel_interview(l,t,local):
    p=entrance(t,55.15,.65)
    txt(l,78,278,'THREE PEOPLE. ONE CONVERSATION.',26,WHITE,True,round(255*p))
    # interactive cards each interviewing "candidate"
    for i in range(3):
        x=62+i*206;y=395
        on=int((local*1.5)%3)==i
        rect(l,(x+5,y+10,x+189,y+337),'#06080E',radius=17,opacity=round(125*p))
        rect(l,(x,y,x+184,y+328),'#172131',outline=ORANGE if on else '#455064',radius=17,width=3,opacity=round(255*p))
        people(l,x+90,y+170,.75,on)
        txt(l,x+20,y+27,f'PANELIST 0{i+1}',16,ORANGE if on else MUTE,True,round(255*p))
        txt(l,x+19,y+283,'LISTENING' if not on else 'ASKING',17,WHITE,True,round(255*p))
        if on:line(l,(x+30,y+265,x+156,y+265),ORANGE,4,round(255*p))
    # geometric tracking lines
    for i in range(3):
        x=154+i*206
        line(l,(x,758,360,812),'#586981',2,round(155*p))
    circle(l,360,811,19,'#1E334A',ORANGE,3,round(255*p))
    txt(l,156,867,'ANSWER THE ASKER',23,ORANGE,True,round(255*p))
    lower_text(l,t,55,70,'04  PANEL INTERVIEW','Then include the entire room in your answer.')


def star(l,t,local):
    p=entrance(t,70.15,.65)
    txt(l,81,277,'STRUCTURE YOUR STORY',27,WHITE,True,round(255*p))
    cards=[('S','SITUATION','Set the context'),('T','TASK','State your goal'),('A','ACTION','Explain your part'),('R','RESULT','Show the outcome')]
    for i,(letter,title,detail) in enumerate(cards):
        x=64+i%2*304;y=366+(i//2)*216
        a=entrance(t,70.45+i*.5,.55)
        yy=y+(1-a)*45
        rect(l,(x,yy,x+281,yy+183),'#172233',outline=ORANGE if i==int((local*.45)%4) else '#38465B',radius=18,width=3,opacity=round(255*a))
        circle(l,x+59,yy+61,38,'#432B22' if i==int((local*.45)%4) else '#263449',ORANGE,3,round(255*a))
        txt(l,x+44,yy+35,letter,40,WHITE,True,round(255*a))
        txt(l,x+108,yy+44,title,22,ORANGE,True,round(255*a))
        txt(l,x+19,yy+125,detail,19,WHITE,False,round(255*a))
        if i<3:
            xx=x+281 if i%2==0 else x+140
            line(l,(xx,yy+93,xx+(20 if i%2==0 else 0),yy+93+ (0 if i%2==0 else 30)),ORANGE,3,round(230*a))
    lower_text(l,t,70,85,'05  BEHAVIORAL INTERVIEW','Make your contribution and impact clear.')


def recap(l,t,local):
    p=entrance(t,85.15,.6)
    txt(l,71,239,'YOUR NEXT',62,WHITE,True,round(255*p))
    txt(l,71,323,'INTERVIEW?',73,ORANGE,True,round(255*p))
    for i,(title,sub) in enumerate([('PREPARE','one strong example'),('PRACTICE','out loud'),('FOLLOW UP','with a thank-you')]):
        y=480+i*118
        q=entrance(t,85.6+i*.65,.55)
        rect(l,(76,y,644,y+93),'#182434',outline='#485366',radius=17,width=2,opacity=round(q*255))
        circle(l,120,y+46,19,'#39291E',ORANGE,3,round(q*255))
        txt(l,108,y+30,'✓',25,ORANGE,True,round(255*q))
        txt(l,163,y+14,title,23,WHITE,True,round(255*q))
        txt(l,163,y+52,sub,20,MUTE,False,round(255*q))
    txt(l,84,880,'SAVE THIS CHECKLIST',28,ORANGE,True,round(p*255))
    lower_text(l,t,85,98,'NOW YOU HAVE A PLAN','Educational guidance • Not a hiring guarantee.')

DRAW=[hook,phone,video,inperson,panel_interview,star,recap]

def make_base():
    im=base_background()
    d=ImageDraw.Draw(im,'RGBA')
    # camera grid and long-term visual identity
    for y in range(200,1101,120):
        d.line((25,y,695,y),fill=(110,137,166,9),width=1)
    return im

def frame(t):
    global BASE
    if BASE is None:BASE=make_base()
    im=BASE.copy()
    # parallax dust keeps graphics live, does not itself constitute the movement
    parts=Image.new('RGBA',(W,H));d=ImageDraw.Draw(parts,'RGBA')
    for i in range(15):
        x=(i*137+t*(8+i%3*4))%720;y=180+(i*181+t*(12+i%4*3))%880
        d.ellipse((x-1,y-1,x+1,y+1),fill=(255,128,77,30))
    im.alpha_composite(parts)
    idx=next((i for i,(s,e,*_) in enumerate(SEGMENTS) if s<=t<e),len(SEGMENTS)-1)
    s,e,title,_,_=SEGMENTS[idx]
    lay=Image.new('RGBA',(W,H));DRAW[idx](lay,t,t-s)
    im.alpha_composite(lay)
    hdr=Image.new('RGBA',(W,H));scene_bar(hdr,t,idx,title)
    im.alpha_composite(hdr)
    return im.convert('RGB')


def generate_audio(dest: Path, with_voice=True,seconds=DURATION):
    fs=44100;n=int(seconds*fs)
    tv=np.arange(n,dtype=np.float32)/fs
    # Original quiet score, phased bass, slow melody, per-section kinetic risers
    fade=np.minimum(np.minimum(tv/1.25,(seconds-tv)/1.5),1).clip(0,1)
    z=(.011*np.sin(2*np.pi*110*tv)+.007*np.sin(2*np.pi*164.81*tv)+.005*np.sin(2*np.pi*220*tv)) * fade
    for beat in np.arange(.5,seconds,.5):
        end=min(n,int((beat+.15)*fs));start=int(beat*fs)
        if start>=end:continue
        v=np.arange(end-start,dtype=np.float32)/fs
        z[start:end] += .018*np.exp(-v*22)*np.sin(2*np.pi*270*v)
    for s,_,*_ in SEGMENTS[1:]:
        if s>=seconds:break
        start=int(s*fs);end=min(n,start+int(.27*fs)); v=np.arange(end-start,dtype=np.float32)/fs
        rng=np.random.default_rng(s+100)
        z[start:end] += .033*rng.standard_normal(len(v)).astype(np.float32)*np.sin(np.pi*v/.27)**2
    if with_voice:
        if not shutil.which('espeak'):
            raise RuntimeError('Offline eSpeak is required for engineering narration')
        for s,e,_,_,spoken in SEGMENTS:
            if s>=seconds:continue
            with tempfile.TemporaryDirectory() as d:
                path=Path(d)/'voice.wav'
                subprocess.run(['espeak','-v','en-us','-s','159','-a','145','-w',str(path),spoken],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
                with wave.open(str(path),'rb') as wf:
                    raw=np.frombuffer(wf.readframes(wf.getnframes()),dtype='<i2').astype(np.float32)/32768.0
                    fs_voice=wf.getframerate()
                raw=resample_poly(raw,fs//math.gcd(fs,fs_voice),fs_voice//math.gcd(fs,fs_voice)).astype(np.float32)
                available=min(len(raw),int((min(e,seconds)-s-.6)*fs))
                start=int((s+.55)*fs);available=min(available,n-start)
                if available>0:
                    r=raw[:available].copy()
                    ramp=min(int(.2*fs),len(r)//3)
                    if ramp>0:
                        r[:ramp]*=np.linspace(0,1,ramp);r[-ramp:]*=np.linspace(1,0,ramp)
                    z[start:start+available] += .38*r
    z=np.tanh(z*1.2).clip(-.92,.92)
    with wave.open(str(dest),'wb') as wf:
        wf.setnchannels(1);wf.setsampwidth(2);wf.setframerate(fs);wf.writeframes((z*32767).astype('<i2').tobytes())


def produce(output:Path,preview_seconds=0,voice=True):
    output=output.resolve();output.parent.mkdir(parents=True,exist_ok=True)
    seconds=min(DURATION,preview_seconds) if preview_seconds else DURATION
    with tempfile.TemporaryDirectory(prefix='career98-motion-') as tmp:
        audio=Path(tmp)/'score.wav'
        generate_audio(audio,voice,seconds)
        cmd=['ffmpeg','-hide_banner','-nostdin','-loglevel','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s','720x1280','-r',str(FPS),'-i','pipe:0', '-i',str(audio),'-vf','scale=1080:1920:flags=lanczos,format=yuv420p','-c:v','libx264','-preset','veryfast','-crf','23','-r',str(FPS),'-c:a','aac','-b:a','128k','-t',str(seconds),'-movflags','+faststart',str(output)]
        p=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
        try:
            for j in range(FPS*seconds):
                p.stdin.write(frame(j/FPS).tobytes())
            p.stdin.close();err=p.stderr.read();r=p.wait()
        except BaseException:
            p.kill();p.wait();raise
        if r!=0:raise RuntimeError(err.decode(errors='replace')[:2000])
    check=subprocess.run(['ffprobe','-v','error','-of','json','-show_streams','-show_format',str(output)],capture_output=True,text=True,check=True)
    info=json.loads(check.stdout)
    vs=next(s for s in info['streams'] if s['codec_type']=='video')
    aud=any(s['codec_type']=='audio' for s in info['streams'])
    dur=float(info['format']['duration'])
    passed=vs['width']==1080 and vs['height']==1920 and vs['codec_name']=='h264' and aud and abs(seconds-dur)<.2
    report={'video':'5 Job Interview Formats | Career Motion Study','duration_seconds':dur,'resolution':'1080x1920','fps':30,'video_codec':vs['codec_name'],'audio_present':aud,'narration':'offline_espeak_engineering_voice_NOT_premium' if voice else 'none','scene_count':len(SEGMENTS),'topic':'job interviews','scripted_original_explainer':True,'reference_footage_reused':False,'general_topic_generation_ready':False,'requires_owner_approval':True,'auto_publish':False,'paid_services_used':False,'render_status':'passed' if passed else 'failed','chapter_times':CHAPTERS}
    output.with_suffix('.engine_run.json').write_text(json.dumps(report,indent=2))
    if not passed:raise RuntimeError('Technical verification failed')
    return report

def main():
    cli=argparse.ArgumentParser()
    cli.add_argument('--output',type=Path,required=True);cli.add_argument('--preview-seconds',type=int,default=0);cli.add_argument('--no-voice',action='store_true')
    args=cli.parse_args();print(json.dumps(produce(args.output,args.preview_seconds,not args.no_voice),indent=2))
if __name__=='__main__':main()