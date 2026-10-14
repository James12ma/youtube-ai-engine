from __future__ import annotations
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from .errors import UnsafeVisualError

def font(size:int):
    p='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
    if Path(p).exists(): return ImageFont.truetype(p,size)
    return ImageFont.load_default()

def card(kind:str,title:str,text:str,size:tuple[int,int],path:Path,*,demo_path:Path|None=None):
    w,h=size
    if kind=='screen_recording' and not demo_path:
        raise UnsafeVisualError('screen_recording requires genuine recorded demo; no synthetic UI permitted')
    if kind=='chart':
        raise UnsafeVisualError('chart requires a real labelled, evidence-backed dataset; refuse synthetic numerical bars')
    im=Image.new('RGB',size,(14,23,40));draw=ImageDraw.Draw(im)
    for y in range(h):
        draw.line([(0,y),(w,y)],fill=(14+int(y/h*10),23+int(y/h*18),40+int(y/h*26)))
    if demo_path:
        from PIL import ImageOps
        image=Image.open(demo_path).convert('RGB')
        image.thumbnail((int(w*.85),int(h*.7)))
        im.paste(image,((w-image.width)//2,(h-image.height)//2))
    else:
        draw.rounded_rectangle((int(.085*w),int(.18*h),int(.915*w),int(.81*h)),radius=max(8,int(h*.03)),fill=(28,43,67),outline=(60,120,175),width=3)
        title_font=font(max(18,int(h*.062))); subfont=font(max(12,int(h*.033)))
        from textwrap import wrap
        lines=wrap(title or 'AI WORKFLOW', width=24 if w>800 else 18)
        y=int(h*.27)
        for line in lines[:3]:
            draw.text((w//2,y),line,font=title_font,fill=(242,249,255),anchor='ma'); y+=int(h*.085)
        lines=wrap(text or 'Explanatory concept — not a software demo',width=45 if w>800 else 28)
        y=max(y+int(h*.04),int(h*.56))
        for line in lines[:3]:
            draw.text((w//2,y),line,font=subfont,fill=(132,207,239),anchor='ma'); y+=int(h*.05)
        # Visible original line-art motifs, no made-up chart values.
        draw.ellipse((int(w*.11),int(h*.22),int(w*.14),int(h*.27)),fill=(101,208,236))
    path.parent.mkdir(parents=True,exist_ok=True);im.save(path)
    return path
