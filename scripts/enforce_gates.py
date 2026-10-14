#!/usr/bin/env python3
"""Independent strict checks on generated files; no trust in self-reported QC flags."""
from __future__ import annotations
import argparse
import json
import math
import re
import subprocess
from pathlib import Path


def fail(message: str):
    raise ValueError('GATE FAILED: '+message)


def tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+(?:'[a-z0-9]+)?",text.casefold())


def lcs_length(a: list[str], b: list[str]) -> int:
    dp=[0]*(len(b)+1)
    for x in a:
        row=[0]
        for i,y in enumerate(b,1):
            row.append(dp[i-1]+1 if x==y else max(row[-1],dp[i]))
        dp=row
    return dp[-1]


def parse_ass(path: Path) -> list[dict]:
    dialogues=[]
    for line in path.read_text(encoding='utf-8').splitlines():
        if not line.startswith('Dialogue: '):
            continue
        # ASS dialogue fields include 9 commas preceding text.
        parts=line.removeprefix('Dialogue: ').split(',',9)
        if len(parts)!=10: fail('Invalid ASS Dialogue format')
        raw_text = parts[9]
        # ASS karaoke/appearance tags are metadata, not spoken text.
        raw_text = re.sub(r'(?<!\\)\{[^{}]*\}', '', raw_text)
        dialogues.append({'start':ass_seconds(parts[1]),'end':ass_seconds(parts[2]),
                         'text':raw_text.replace('\\N',' ').replace('\\{','{').replace('\\}','}'),
                         'lines':[line.replace('\\{','{').replace('\\}','}')
                                  for line in raw_text.split('\\N')]})
    return dialogues


def ass_seconds(s: str) -> float:
    h,m,seconds=s.split(':')
    return int(h)*3600+int(m)*60+float(seconds)


def validate_alignment(transcript: str, words: list, duration: float, min_coverage:float=0.98):
    expected=tokens(transcript)
    actual=tokens(' '.join(w['word'] for w in words))
    if len(expected)<4: fail('Transcript too short')
    ratio=lcs_length(expected, actual)/len(expected)
    if ratio<min_coverage: fail(f'Incomplete transcript alignment: {ratio:.3f}')
    prev_end=0.0
    for i,w in enumerate(words):
        start,end=float(w['start_s']),float(w['end_s'])
        if not all(map(math.isfinite,(start,end))):fail('NaN/inf timestamps')
        if start < -0.02 or end > duration+0.05 or end<=start:fail('Invalid timestamp')
        if start < prev_end-0.08:fail(f'Overlapping word at index {i}')
        prev_end=end
    return ratio


def validate_captions(words:list, ass:list, duration:float):
    if not ass: fail('Missing captions')
    transcript_words=tokens(' '.join(w['word'] for w in words))
    caption_words=tokens(' '.join(d['text'] for d in ass))
    if transcript_words!=caption_words:fail('Captions omit or reorder speech words')
    prev_end=0.0
    for d in ass:
        if d['start']<-0.02 or d['end']<=d['start'] or d['end']>duration+0.06:
            fail('Caption outside audio bounds')
        if d['start']<prev_end-0.03:fail('Captions overlap')
        prev_end=d['end']
        if len(d['lines'])>2 or any(len(line)>32 for line in d['lines']):
            fail('Caption line exceeds two lines or 32 characters')
    # Every aligned word's midpoint must be visible under some cue.
    covered=sum(any(d['start']-0.04 <= (float(w['start_s'])+float(w['end_s']))/2
                      <= d['end']+0.04 for d in ass) for w in words)
    if covered/len(words)<0.98:fail('Insufficient time-aligned caption coverage')
    return covered/len(words)


def probe_mp4(path:Path)->dict:
    p=subprocess.run(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(path)],
                     capture_output=True,text=True,check=True)
    return json.loads(p.stdout)


def measure_loudness(path:Path)->tuple[float,float]:
    p=subprocess.run(['ffmpeg','-hide_banner','-nostats','-i',str(path),'-af',
                      'loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json','-f','null','-'],
                     capture_output=True,text=True,check=True)
    match=re.search(r'\{[^{}]*"input_i"[^{}]*\}',p.stderr,re.S)
    if not match:fail('Could not measure loudness')
    obj=json.loads(match.group())
    return float(obj['input_i']),float(obj['input_tp'])


def enforce(out:Path, do_probe:bool=True, expected_size:tuple[int,int]=(1920,1080))->dict:
    for name in ('vo.wav','vo_norm.wav','words.json','captions.ass','final.mp4','qc_report.json'):
        f=out/name
        if not f.is_file() or f.stat().st_size==0: fail('Missing '+name)
    qc=json.loads((out/'qc_report.json').read_text(encoding='utf-8'))
    data=json.loads((out/'words.json').read_text(encoding='utf-8'))
    if qc.get('aligner_ran') is not True or data.get('method') != 'whisperx_ctc':
        fail('Real WhisperX CTC alignment not confirmed')
    if data.get('transcript') != qc.get('transcript'):fail('Mismatched transcripts')
    words=data.get('words',[])
    duration=float(data['duration_s'])
    if not words:fail('Zero words aligned')
    coverage=validate_alignment(data['transcript'],words,duration)
    ass=parse_ass(out/'captions.ass')
    caption_coverage=validate_captions(words,ass,duration)
    if do_probe:
        info=probe_mp4(out/'final.mp4')
        v=[s for s in info['streams'] if s['codec_type']=='video']
        a=[s for s in info['streams'] if s['codec_type']=='audio']
        if len(v)!=1 or len(a)!=1: fail('MP4 stream count invalid')
        if (v[0]['width'],v[0]['height']) !=expected_size: fail('MP4 wrong resolution')
        if v[0]['codec_name']!='h264' or a[0]['codec_name']!='aac':
            fail('MP4 unexpected codecs')
        video_length=float(info['format']['duration'])
        if abs(video_length-duration)>0.45:fail('MP4 duration drifts from speech')
        lufs,tp=measure_loudness(out/'final.mp4')
        if not all(map(math.isfinite,(lufs,tp))):fail('Nonfinite loudness')
        if abs(lufs+16)>1.5:fail(f'Output loudness {lufs} outside -16 ±1.5 LUFS')
        if tp>-1.0:fail(f'True peak {tp} exceeds -1.0 dBTP')
    return {'real_alignment':True,'token_coverage':coverage,
            'caption_coverage':caption_coverage,'word_count':len(words),
            'caption_blocks':len(ass),'mp4_probed':do_probe}

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--out-dir',type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(enforce(args.out_dir),indent=2))
