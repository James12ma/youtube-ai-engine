from __future__ import annotations
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from .errors import UnsafeVisualError

def font(size:int):
    p='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
    if Path(p).exists(): return ImageFont.truetype(p,size)
    return ImageFont.load_default()

def fit_text(draw,text:str,max_width:int,size:int,min_size:int,max_lines:int):
    """Largest font (down to min_size) whose word-wrapped lines fit max_width in max_lines."""
    words=text.split()
    while True:
        f=font(size)
        lines=[];cur=''
        for word in words:
            trial=(cur+' '+word).strip()
            if not cur or draw.textlength(trial,font=f)<=max_width:cur=trial
            else:lines.append(cur);cur=word
        if cur:lines.append(cur)
        fits=all(draw.textlength(l,font=f)<=max_width for l in lines)
        if (len(lines)<=max_lines and fits) or size<=min_size:
            if len(lines)>max_lines:
                lines=lines[:max_lines];lines[-1]=lines[-1].rstrip('.,;:')+'…'
            return f,lines
        size=max(min_size,int(size*.9))

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
        portrait=h>w
        box=((int(.06*w),int(.10*h),int(.94*w),int(.58*h)) if portrait
             else (int(.085*w),int(.18*h),int(.915*w),int(.81*h)))
        draw.rounded_rectangle(box,radius=max(8,int(min(w,h)*.03)),fill=(28,43,67),outline=(60,120,175),width=3)
        inner=int((box[2]-box[0])*.86)
        title_font,title_lines=fit_text(draw,title or 'AI WORKFLOW',inner,
            int(w*.085) if portrait else int(h*.062),18,3)
        sub_font,sub_lines=fit_text(draw,text or 'Explanatory concept — not a software demo',inner,
            int(w*.046) if portrait else int(h*.033),12,4)
        step=int(title_font.size*1.25) if hasattr(title_font,'size') else 24
        sub_step=int(sub_font.size*1.35) if hasattr(sub_font,'size') else 16
        gap=int((box[3]-box[1])*.06)
        block=step*len(title_lines)+gap+sub_step*len(sub_lines)
        y=box[1]+max(int((box[3]-box[1])*.10),((box[3]-box[1])-block)//2)
        for line in title_lines:
            draw.text((w//2,y),line,font=title_font,fill=(242,249,255),anchor='ma'); y+=step
        y+=gap
        for line in sub_lines:
            if y+sub_step>box[3]-int((box[3]-box[1])*.04):break
            draw.text((w//2,y),line,font=sub_font,fill=(132,207,239),anchor='ma'); y+=sub_step
        # Visible original line-art motifs, no made-up chart values.
        d=int(min(w,h)*.03)
        draw.ellipse((box[0]+d,box[1]+d,box[0]+2*d,box[1]+2*d),fill=(101,208,236))
    path.parent.mkdir(parents=True,exist_ok=True);im.save(path)
    return path
