from __future__ import annotations
from pathlib import Path
from .models import WordTiming

def group_words(words:list[WordTiming],max_chars=32,max_lines=2,max_dur=4.):
    if not words: return []
    blocks=[]; current=[]; lines=[]
    def flush():
        if current:
            blocks.append({'start_s':current[0].start_s,'end_s':max(current[-1].end_s,current[0].start_s+.25),'text':'\\N'.join(lines)})
    for word in words:
        if len(word.text)>max_chars: raise ValueError('word too long for caption line')
        prospective=list(lines)
        if not prospective: prospective=[word.text]
        elif len(prospective[-1]) + 1 + len(word.text) <= max_chars: prospective[-1] += ' '+word.text
        else: prospective.append(word.text)
        if current and (len(prospective)>max_lines or word.end_s-current[0].start_s>max_dur or word.start_s-current[-1].end_s>.7):
            flush(); current=[]; lines=[]; prospective=[word.text]
        current.append(word); lines=prospective
    flush(); return blocks

def fmt(t:float):
    cs=round(max(t,0)*100);h,cs=divmod(cs,360000);m,cs=divmod(cs,6000);s,c=divmod(cs,100)
    return f'{h}:{m:02d}:{s:02d}.{c:02d}'

def escape_ass(text:str):
    # Remove override-control delimiters; preserve explicit line separator.
    return text.replace('{','(').replace('}',')').replace('\r',' ').replace('\n',' ').replace('\\N','\\N')

def write_ass(blocks:list[dict],dest:Path,width:int,height:int,font='DejaVu Sans',size=48)->int:
    header="""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 2
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font},{size},&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,1,2,80,80,45,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""".format(width=width,height=height,font=font,size=size)
    dest.parent.mkdir(exist_ok=True,parents=True)
    events=[f'Dialogue: 0,{fmt(b["start_s"])},{fmt(b["end_s"])},Default,,0,0,0,,{escape_ass(b["text"])}' for b in blocks]
    dest.write_text(header+'\n'.join(events)+'\n',encoding='utf-8')
    return len(events)
