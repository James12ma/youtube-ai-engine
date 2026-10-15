"""Readable two-line ASS captions and independent timing coverage checks."""
from __future__ import annotations
import re
import math
from pathlib import Path
from pydantic import BaseModel
from .aligner import WordTimestamp, _tokens

ASS_HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: {w}
PlayResY: {h}
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,DejaVu Sans,{size},&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,1,2,80,80,60,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

class CaptionQualityReport(BaseModel):
    total_words: int
    captions_emitted: int
    words_covered: int
    coverage_ratio: float
    words_outside_audio: int
    overlapping_captions: int
    text_match_ratio: float
    passed: bool
    failures: list[str]

def _fmt(s):
    return f"{int(s//3600)}:{int(s%3600//60):02d}:{s%60:05.2f}"

def _ass_escape(text: str) -> str:
    return text.replace("\\","\\\\").replace("{","\\{").replace("}","\\}").replace("\n"," ")

def _wrap(words: list[WordTimestamp], max_chars: int,max_lines: int):
    lines=[]; line=""
    for word in words:
        piece=word.word
        if len(piece)>max_chars:
            raise ValueError("unbreakable word exceeds caption line length")
        trial=(line+" "+piece).strip()
        if len(trial) > max_chars:
            lines.append(line); line=piece
        else: line=trial
    if line: lines.append(line)
    if len(lines)>max_lines: raise ValueError("caption exceeds maximum line count")
    return lines

def build_ass_from_words(words:list[WordTimestamp], output_path: Path, *, width:int, height:int,
                         size:int=48, max_chars_per_line:int=32, max_lines:int=2,
                         max_duration_s:float=4.0, gap_threshold_s:float=0.6,
                         animated:bool=False, bottom_margin:int|None=None):
    if not words: raise ValueError("word alignments are empty")
    blocks=[]; group=[]
    def flush():
        nonlocal group
        if group:
            lines=_wrap(group,max_chars_per_line,max_lines)
            blocks.append(dict(start_s=group[0].start_s,end_s=group[-1].end_s,
                               text="\\N".join(lines),words=[w.word for w in group]))
            group=[]
    for word in words:
        proposal=group+[word]
        requires_split=False
        if group:
            if word.end_s-group[0].start_s > max_duration_s or word.start_s-group[-1].end_s>gap_threshold_s:
                requires_split=True
            else:
                try: _wrap(proposal,max_chars_per_line,max_lines)
                except ValueError: requires_split=True
        if requires_split: flush()
        _wrap([word],max_chars_per_line,max_lines)
        group.append(word)
    flush()
    output_path.parent.mkdir(parents=True,exist_ok=True)
    lines=[ASS_HEADER.format(w=width,h=height,size=size)]
    if bottom_margin is not None:
        lines[0]=lines[0].replace(',80,80,60,1',f',80,80,{bottom_margin},1')
    if animated:
        lines[0]=lines[0].replace('&H00FFFFFF,&H000000FF','&H00C5E76C,&H00FFFFFF')
    position=0
    for block in blocks:
        text="\\N".join(_ass_escape(s) for s in block["text"].split("\\N"))
        if animated:
            group_words=words[position:position+len(block['words'])]
            position+=len(group_words)
            cursor=round(group_words[0].start_s*100)
            pieces=[];line_chars=0
            for word in group_words:
                start=round(word.start_s*100);end=round(word.end_s*100)
                if line_chars and line_chars+1+len(word.word)>max_chars_per_line:
                    pieces.append('\\N');line_chars=0
                elif line_chars:
                    pieces.append(' ');line_chars+=1
                if start>cursor:pieces.append('{\\k'+str(start-cursor)+'}')
                pieces.append('{\\kf'+str(max(1,end-max(cursor,start)))+'}'+_ass_escape(word.word))
                cursor=max(cursor,end);line_chars+=len(word.word)
            text='{\\fad(50,70)}'+''.join(pieces)
        lines.append("Dialogue: 0,"+_fmt(block["start_s"])+","+_fmt(block["end_s"])+",Default,,0,0,0,,"+text)
    output_path.write_text("\n".join(lines)+"\n",encoding="utf-8")
    return len(blocks),blocks

def assess_caption_quality(words:list[WordTimestamp], blocks:list[dict],audio_duration_s:float,*,min_coverage=0.98):
    failures=[]; covered=0;outside=0;overlap=0
    for word in words:
        if any(b["start_s"]-0.02<=word.start_s and word.end_s<=b["end_s"]+0.02 for b in blocks):
            covered+=1
    coverage=covered/len(words) if words else 0.0
    if coverage<min_coverage: failures.append("timing coverage below threshold")
    for b in blocks:
        if b["start_s"] < -0.02 or b["end_s"] > audio_duration_s+0.04 or b["end_s"]<=b["start_s"]: outside+=1
    if outside: failures.append("caption interval invalid/outside audio")
    for i in range(len(blocks)-1):
        if blocks[i+1]["start_s"] < blocks[i]["end_s"]-0.02: overlap+=1
    if overlap: failures.append("overlapping captions")
    actual=_tokens(" ".join(" ".join(b.get("words",[])) for b in blocks))
    expected=_tokens(" ".join(w.word for w in words))
    text_match=1 if expected==actual else 0
    if not text_match: failures.append("caption text missing/reordered words")
    return CaptionQualityReport(total_words=len(words),captions_emitted=len(blocks),
        words_covered=covered,coverage_ratio=coverage,words_outside_audio=outside,
        overlapping_captions=overlap,text_match_ratio=text_match,passed=not failures,failures=failures)


def save_srt_from_blocks(blocks:list[dict], output_path:Path) -> Path:
    """Plain-text sidecar from validated alignment blocks, at millisecond precision."""
    if not blocks: raise ValueError('Caption blocks are empty')
    def stamp(ms):
        hours,ms=divmod(ms,3600000);minutes,ms=divmod(ms,60000);seconds,ms=divmod(ms,1000)
        return f'{hours:02}:{minutes:02}:{seconds:02},{ms:03}'
    cues=[];previous=0
    for index,block in enumerate(blocks,1):
        start,end=block['start_s'],block['end_s']
        if not all(math.isfinite(t) for t in (start,end)) or start<0 or end<=start:
            raise ValueError('Invalid SRT interval')
        a,b=round(start*1000),round(end*1000)
        if a<previous or b<=a:raise ValueError('Overlapping or empty SRT interval')
        previous=b
        text=' '.join(str(word).replace('\r',' ').replace('\n',' ') for word in block['words'])
        if not text.strip():raise ValueError('Empty SRT text')
        cues.append(f'{index}\n{stamp(a)} --> {stamp(b)}\n{text}')
    output_path=Path(output_path);output_path.parent.mkdir(parents=True,exist_ok=True)
    output_path.write_text('\n\n'.join(cues)+'\n',encoding='utf-8')
    return output_path
