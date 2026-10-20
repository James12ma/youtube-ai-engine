"""Offline 60-second career interview motion adapter for YouTube AI Engine.

Real procedural animation and original local music. No network calls, paid APIs,
upload, publication, or auto-approved quality claims.
"""
from __future__ import annotations
import math,wave,subprocess,shutil,tempfile
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import numpy as np

W,H=720,1280
FPS=24
DUR=60
INK='#151619';RED='#d63834';GRAY='#6e706e';WHITE='#f8f8f5';PALE='#e2e3df'
F={
 'b':('/usr/share/fonts/opentype/inter/InterDisplay-Black.otf','/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'),
 'm':('/usr/share/fonts/opentype/inter/InterDisplay-Medium.otf','/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),
 's':('/usr/share/fonts/opentype/inter/InterDisplay-SemiBold.otf','/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'),
 'i':('/usr/share/fonts/truetype/noto/NotoSerif-BoldItalic.ttf','/usr/share/fonts/truetype/dejavu/DejaVuSerifCondensed-BoldItalic.ttf','/usr/share/fonts/truetype/liberation2/LiberationSerif-BoldItalic.ttf','/usr/share/fonts/truetype/liberation/LiberationSerif-BoldItalic.ttf','/usr/share/fonts/opentype/urw-base35/NimbusRoman-BoldItalic.otf'),
}
CACHE={}
def ft(size,style='b'):
 k=(size,style)
 if k not in CACHE:
  paths=[v for v in F[style] if Path(v).exists()]
  if not paths:raise RuntimeError('Fonts missing: install DejaVu Sans/Serif before rendering')
  CACHE[k]=ImageFont.truetype(paths[0],size)
 return CACHE[k]
def tx(d,x,y,s,size=35,c=INK,style='b'):d.text((int(x),int(y)),s,font=ft(size,style),fill=c)
def rr(d,box,r=20,fill=WHITE,outline=None,width=2):d.rounded_rectangle(tuple(int(q) for q in box),radius=r,fill=fill,outline=outline,width=width)
def e(a):a=max(0,min(1,a));return a*a*(3-2*a)
def head(d,x,y,k=1,red=False):
 r=int(24*k);x=int(x);y=int(y)
 d.ellipse((x-r,y-r,x+r,y+r),fill='#242526',outline='#606365',width=2)
 rr(d,(x-r*1.4,y+r*.85,x+r*1.4,y+r*2.9),int(r*.45),'#303133')
 if red:d.polygon([(x,y+r),(x-5,y+r*1.65),(x,y+r*2.35),(x+5,y+r*1.65)],fill=RED)
def tag(d,x,y,s,active=False):
 w=d.textbbox((0,0),s,font=ft(17,'s'))[2]+38
 rr(d,(x,y,x+w,y+39),12,INK if active else WHITE,outline=INK if active else '#b5b7b3',width=1)
 tx(d,x+18,y+11,s,17,'white' if active else INK,'s')
def common(d,t,n,label):
 rr(d,(43,71,243,111),18,INK);tx(d,59,82,'CAREER / NOTES',16,'white','s')
 tx(d,549,82,f'{n:02d} / 05',17,INK,'s');d.line((43,125,675,125),fill=INK,width=2)
 d.line((43,1195,675,1195),fill=INK,width=1)
 tx(d,43,1213,'FIELD GUIDE  /  JOB SKILLS',15,GRAY,'s');tx(d,625,1213,f'{int(t):02d}s',16,GRAY,'s')
 tx(d,43,169,label,23,RED,'s')
def tip(d,s):
 rr(d,(43,1056,676,1158),23,'#fffefd',outline='#c4c6c2')
 tx(d,66,1073,'THE MOVE',17,RED,'s');tx(d,66,1111,s,24,INK,'s')
rng=np.random.default_rng(11);yy,xx=np.mgrid[:H,:W]
b=(248-8*yy/H+rng.normal(0,.9,(H,W))).clip(0,255).astype('uint8');a=np.dstack((b,b,b))
BG=Image.fromarray(a,'RGB');bd=ImageDraw.Draw(BG)
for i in range(41,W,78):bd.line((i,0,i,H),fill='#eaeae6',width=1)
for i in range(38,H,78):bd.line((0,i,W,i),fill='#ecece8',width=1)
N=400;ox,oy=np.meshgrid(np.arange(N),np.arange(N));u=(ox-N/2)/(N*.48);v=(oy-N/2)/(N*.48);rad=np.sqrt(u*u+v*v)
val=19+62*np.maximum(0,1-np.sqrt((u+.20)**2+(v+.28)**2))+145*np.exp(-((u+.36)**2/.04+(v+.49)**2/.02))+42*np.exp(-((rad-.91)**2)/.014)*np.maximum(0,-u)
orbimg=np.dstack((np.clip(val*.94,0,255),np.clip(val,0,255),np.clip(val*1.03,0,255),np.clip((1-rad)*32,0,1)*255)).astype('uint8')
ORB=Image.fromarray(orbimg,'RGBA');SPRITES={}
def orb(im,x,y,size):
 size=int(size)
 if size not in SPRITES:SPRITES[size]=ORB.resize((size,size),Image.Resampling.BILINEAR)
 sp=SPRITES[size];im.paste(sp,(int(x-size/2),int(y-size/2)),sp)
def body(t):
 im=BG.copy();d=ImageDraw.Draw(im)
 # Quiet moving grid cursor: background motion under the illustrated objects.
 sweep_x=42+int((t*160)%590)
 d.line((sweep_x,145,sweep_x,1180),fill='#dcded9',width=3)
 if t<8:
  common(d,t,0,'60 SECONDS. MORE CONFIDENCE.')
  tx(d,42,236,'5 TYPES OF',74);tx(d,42,325,'JOB',133);tx(d,42,475,'INTERVIEWS',62);tx(d,48,561,'explained.',70,RED,'i')
  d.ellipse((118,734,598,1095),outline='#c9cbc6',width=2)
  d.arc((118,734,598,1095),-25,118,fill=RED,width=7)
  orb(im,365+8*math.sin(t),907+8*math.cos(t),290)
  for i in range(6):
   ang=i*math.tau/6+t*.18;orb(im,365+236*math.cos(ang),907+162*math.sin(ang),26+i%3*8)
  tx(d,48,1140,'FIVE FORMATS. FIVE SMART MOVES.',21,INK,'s')
 elif t<18:
  s=t-8;common(d,t,1,'01 — FACE TO FACE')
  tx(d,43,227,'IN PERSON',78);tx(d,46,334,'Make the first moment count.',26,GRAY,'m')
  d.ellipse((92,802,639,957),fill='#dcdeda')
  head(d,192+8*math.sin(s*.3),622,1.6,True);head(d,510,615,1.55)
  d.polygon([(209,802),(508,802),(609,863),(115,863)],fill='#393a3b')
  d.polygon([(115,863),(609,863),(602,883),(128,883)],fill=INK)
  d.line((169,879,151,957),fill='#38393a',width=17);d.line((552,879,572,957),fill='#38393a',width=17)
  d.polygon([(324,782),(409,782),(437,835),(344,835)],fill='#faf9f5')
  for k in range(3):d.line((344,793+12*k,404,793+12*k),fill='#b2b4b0',width=2)
  tag(d,59,959,'ARRIVE EARLY',True);tip(d,'Bring a copy of your résumé.')
 elif t<28:
  common(d,t,2,'02 — FIRST CONTACT')
  tx(d,43,227,'PHONE',103);tx(d,43,334,'SCREEN',102);tx(d,46,459,'Your voice is the first impression.',24,GRAY,'m')
  x1,y1,x2,y2=201,536,520,992
  rr(d,(x1,y1,x2,y2),52,'#1b1d1f');rr(d,(x1+13,y1+14,x2-13,y2-14),41,'#343638')
  rr(d,(x1+25,y1+26,x2-25,y2-26),32,'#232527')
  rr(d,(311,560,408,576),8,'#050606')
  tx(d,267,628,'RECRUITER',24,'#f3f4f0','s');tx(d,281,666,'Incoming call',17,'#aeb0ad','m')
  for i in range(13):
   z=abs(math.sin(t*5+i*.6));h=13+z*63;xx=245+i*18
   rr(d,(xx,755-h/2,xx+9,755+h/2),4,RED if i%5==0 else '#e5e7e4')
  d.ellipse((326,838,396,908),fill='#489268');tx(d,350,854,'✓',32,'white')
  tag(d,51,565,'QUIET ROOM',True);tag(d,474,919,'NOTES READY');tip(d,'Find a quiet space. Keep notes close.')
 elif t<38:
  common(d,t,3,'03 — ON CAMERA')
  tx(d,43,227,'VIDEO',105);tx(d,43,342,'CALL',105)
  tx(d,46,467,'Make the technology invisible.',26,GRAY,'m')
  rr(d,(60,554,663,977),33,'#1f2224');rr(d,(78,571,644,958),16,'#eef0ed')
  for k,(ax,ay) in enumerate([(92,587),(368,587),(92,765),(368,765)]):
   rr(d,(ax,ay,ax+259,ay+165),11,['#e4e6e1','#d8dad7','#e1e3df','#d5d8d4'][k]);head(d,ax+129,ay+45,.7,k==0)
   tx(d,ax+13,ay+130,['YOU','HIRING LEAD','TEAM MEMBER','RECRUITER'][k],14,INK,'s')
  rr(d,(518,593,635,624),13,INK);d.ellipse((530,603,541,614),fill=RED);tx(d,551,602,'LIVE',14,'white','s')
  d.polygon([(53,977),(668,977),(700,1005),(21,1005)],fill='#5b5d5e')
  tag(d,44,1016,'CAMERA + MIC',True);tip(d,'Test your sound, camera, and lighting.')
 elif t<48:
  common(d,t,4,'04 — MULTIPLE INTERVIEWERS')
  tx(d,43,229,'PANEL',114);tx(d,47,352,'Connect with the whole room.',26,GRAY,'m')
  cx,cy=357,749
  for r in [170,244]:d.ellipse((cx-r,cy-r,cx+r,cy+r),outline='#cfd1cc',width=2)
  for i,ang in enumerate([-2.38,-1.57,-.77]):
   px=cx+224*math.cos(ang);py=cy+226*math.sin(ang)
   d.line((cx,cy+105,px,py+50),fill='#c6c9c3',width=3)
   d.ellipse((px-73,py-83,px+73,py+70),fill='#f6f6f2',outline=RED if i==int(t*1.2)%3 else '#c3c6c0',width=5 if i==int(t*1.2)%3 else 2)
   head(d,px,py-24,.86,i==1)
  d.ellipse((cx-103,cy+21,cx+103,cy+235),fill='#eceeea',outline='#c6c8c3',width=2)
  head(d,cx,cy+62,1.12,True)
  tag(d,48,994,'EYE CONTACT',True);tip(d,'Answer, then include everyone.')
 elif t<56:
  s=t-48;common(d,t,5,'05 — SHOW YOUR SKILLS')
  tx(d,43,231,'SKILLS',112);tx(d,43,350,'TEST',107)
  tx(d,46,467,'Show your thinking, not just the result.',25,GRAY,'m')
  rr(d,(47,550,671,997),26,'#fffefd',outline='#bfc3bd')
  rr(d,(47,550,671,613),24,INK);d.rectangle((47,588,671,613),fill=INK)
  for j,col in enumerate([RED,'#d9b353','#6ba891']):d.ellipse((70+j*24,574,83+j*24,587),fill=col)
  tx(d,242,572,'ASSESSMENT  /  01',17,'white','s');tx(d,79,630,'Build a simple budget',28,INK,'s')
  for row in range(5):
   for col in range(3):
    x1=78+col*183;y1=705+row*51
    rr(d,(x1,y1,x1+177,y1+44),4,'#f0f1ed' if row%2==0 else '#fafbf7',outline='#d7d9d4',width=1)
    lab=[['CATEGORY','COST','STATUS'],['Rent','$900','●'],['Food','$250','●'],['Travel','$85','●'],['Savings','$200','●']][row][col]
    tx(d,x1+11,y1+12,lab,15 if row==0 else 18,RED if col==2 and row>0 and row<2+int(s/2) else INK,'s' if row==0 else 'm')
  tag(d,45,1009,'SHOW YOUR PROCESS',True);tip(d,'Talk through the steps you take.')
 else:
  common(d,t,5,'YOUR NEXT INTERVIEW')
  d.ellipse((118,221,597,700),outline='#bdc0ba',width=2);d.arc((118,221,597,700),int(t*30)%360,int(t*30)%360+105,fill=RED,width=7)
  orb(im,354,455,279)
  tx(d,40,770,'PREPARE FOR',63);tx(d,42,851,'THE',96)
  tx(d,43,961,'format.',89,RED,'i')
  rr(d,(44,1090,675,1161),20,INK);tx(d,97,1110,'SAVE THIS GUIDE   ↗',29,'white','s')
 start=0 if t<8 else 8 if t<18 else 18 if t<28 else 28 if t<38 else 38 if t<48 else 48 if t<56 else 56
 dt=t-start
 if dt<.32:
  w=int(W*(1-e(dt/.32)));d.rectangle((0,0,w,H),fill=WHITE);d.rectangle((w-5,0,w,H),fill=RED)
 # Animated editorial side marker prevents frozen stretches in explanatory shots.
 marker_y=196+int((t*600)%770)
 d.rounded_rectangle((19,marker_y,33,marker_y+74),radius=5,fill=RED)
 d.rectangle((0,H-9,int(W*t/DUR),H),fill=RED)
 return im

def music(path: Path):
 sr=44100;n=sr*60;times=np.arange(n)/sr;out=np.zeros(n)
 for freq in [110,164.8,220,329.6]:out+=.017*np.sin(times*math.tau*freq+.17*np.sin(times*1.3))
 notes=[220,261.6,329.6,293.7,246.9,329.6,392,329.6]
 for j,bt in enumerate(np.arange(0,60,.5)):
  st=int(bt*sr);dur=int(.27*sr);v=np.arange(dur)/sr
  out[st:st+dur]+=.04*np.exp(-v*14)*np.sin(math.tau*notes[j%8]*v)
  out[st:st+dur]+=.045*np.exp(-v*34)*np.sin(math.tau*(57*v+15*v*v))
 for bt in [0,8,18,28,38,48,56]:
  st=int(bt*sr);dur=int(.4*sr);v=np.arange(dur)/sr
  out[st:st+dur]+=.06*np.exp(-v*16)*np.sin(math.tau*(540*v+180*v*v))
 out*=np.minimum(1,times/.4)*np.minimum(1,(60-times)/1.3)
 out=np.tanh(out*1.7)*.75
 with wave.open(str(path),'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(sr);w.writeframes((out*32767).astype('<i2').tobytes())

def render_career(output: Path, *, preview: bool = False, music_enabled: bool = True) -> dict:
 """Render the 60-second interview explainer. Preview renders first 4 seconds.

 Native procedural canvas: 720x1280@24; exports upscaled 1080x1920@24.
 """
 if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
  raise RuntimeError("FFmpeg and ffprobe are required")
 output=Path(output).resolve();output.parent.mkdir(parents=True,exist_ok=True)
 duration=4 if preview else DUR
 with tempfile.TemporaryDirectory(prefix="yt-engine-career-") as tmp:
  raw=Path(tmp)/"silent.mp4"
  cmd=["ffmpeg","-hide_banner","-loglevel","error","-y","-f","rawvideo",
       "-pix_fmt","rgb24","-s",f"{W}x{H}","-r",str(FPS),"-i","-",
       "-c:v","libx264","-preset","veryfast","-crf","19",
       "-pix_fmt","yuv420p",str(raw)]
  proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
  try:
   assert proc.stdin is not None
   for frame in range(duration*FPS):proc.stdin.write(body(frame/FPS).tobytes())
   proc.stdin.close()
   err=proc.stderr.read().decode('utf-8','replace') if proc.stderr else ''
   if proc.stderr:proc.stderr.close()
   if proc.wait():raise RuntimeError('Video encoder failed: '+err[-1000:])
  except BaseException:
   if proc.poll() is None:proc.kill()
   proc.wait()
   raise
  wav=Path(tmp)/"score.wav"
  if music_enabled:music(wav)
  args=["ffmpeg","-hide_banner","-loglevel","error","-y","-i",str(raw)]
  if music_enabled:args += ["-i",str(wav)]
  args += ["-vf","scale=1080:1920:flags=lanczos","-c:v","libx264",
           "-preset","veryfast","-crf","19","-pix_fmt","yuv420p"]
  if music_enabled:args += ["-c:a","aac","-b:a","160k","-shortest"]
  else:args += ["-an"]
  args += ["-t",str(duration),"-movflags","+faststart",str(output)]
  subprocess.run(args,check=True,capture_output=True,text=True)
 return {"output":str(output),"duration_seconds":duration,"fps":FPS,
         "width":1080,"height":1920,"native_canvas":"720x1280",
         "has_original_score":music_enabled,"auto_publish":False}
