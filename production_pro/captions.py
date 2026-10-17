"""ASS captions. Timestamps are approximate unless an external forced aligner is used."""
from __future__ import annotations
import re
from pathlib import Path
from .models import NarrationResult

HEADER='''[Script Info]
ScriptType: v4.00+
PlayResX: {w}
PlayResY: {h}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,DejaVu Sans,{size},&H00FFFFFF,&H000000FF,&H00101827,&H7F101827,-1,0,0,0,100,100,0,0,1,3,1,2,80,80,70,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
def _ts(seconds):
 h=int(seconds//3600);m=int((seconds%3600)//60);s=seconds-h*3600-m*60
 return f'{h}:{m:02d}:{s:05.2f}'
def _escape(s):
 return s.replace('\\','\\\\').replace('{','').replace('}','').replace('\n',' ')

def _chunks(words,max_chars=30,max_lines=2):
 blocks=[]; block=[]
 for word in words:
  if len(word)>max_chars: raise ValueError('A word exceeds caption line width')
  candidate=block+[word]
  try:
   _wrap_caption(candidate,max_chars)
  except ValueError:
   if not block: raise
   blocks.append(block)
   block=[word]
  else:
   if len(candidate)>7:
    blocks.append(block);block=[word]
   else:block=candidate
 if block:blocks.append(block)
 return blocks

def _wrap_caption(words,max_chars,*,escape=False):
 lines=[''];
 for w in words:
  candidate=(lines[-1]+' '+w).strip()
  if len(candidate)>max_chars and lines[-1]:lines.append(w)
  else:lines[-1]=candidate
 if len(lines)>2 or any(len(l)>max_chars for l in lines):raise ValueError('caption wrapping overflow')
 # Escape the TEXT before inserting ASS's structural line break. Escaping
 # the already joined string doubles \\N and draws a stray backslash.
 return r'\N'.join(_escape(line) if escape else line for line in lines)

def write_captions(narration:NarrationResult,path:Path,width:int,height:int,max_chars=30)->tuple[int,float,bool]:
 out=[HEADER.format(w=width,h=height,size=(42 if width>=1920 else 33 if width>=1280 else 25))];offset=0.;n=0;covered=0.
 for segment in narration.segments:
  words=segment.text.split(); allchars=sum(len(x) for x in words)
  elapsed=0.;
  for block in _chunks(words,max_chars):
   # Relative text length only estimates boundaries; do NOT label as forced aligned.
   ratio=sum(len(x) for x in block)/max(1,allchars)
   duration=segment.duration_s*ratio
   start=offset+elapsed; end=min(offset+segment.duration_s, start+duration)
   if end-start>=0.08:
    out.append(f'Dialogue: 0,{_ts(start)},{_ts(end)},Default,,0,0,0,,{_wrap_caption(block,max_chars,escape=True)}')
    covered+=end-start;n+=1
   elapsed+=duration
  offset+=segment.duration_s
 path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text('\n'.join(out)+'\n',encoding='utf-8')
 coverage=min(1.,covered/max(narration.total_duration_s,1e-6))
 return n,coverage,False
