#!/usr/bin/env python3
"""Opt-in REAL Piper + WhisperX CPU integration. Never estimates timestamps.

Importing or unit testing this file makes no external requests. In production
it downloads only model assets via the explicitly configured tool/runtime.
"""
from __future__ import annotations
import argparse
import json
import re
import subprocess
from pathlib import Path
from narration_pro import (
    PiperNarrator, WhisperXAligner, normalize_loudness,
    build_ass_from_words, assess_caption_quality, save_word_timestamps
)


def run_cmd(args: list[str]) -> subprocess.CompletedProcess:
    p = subprocess.run(args, capture_output=True, text=True)
    if p.returncode:
        raise RuntimeError(f"Command failed ({args[0]}): {p.stderr[-600:]}")
    return p


def ffprobe(path: Path) -> dict:
    return json.loads(run_cmd(['ffprobe','-v','error','-show_format','-show_streams',
                               '-of','json',str(path)]).stdout)


def measure(path: Path) -> tuple[float,float]:
    p = run_cmd(['ffmpeg','-hide_banner','-nostats','-i',str(path),'-af',
                 'loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json','-f','null','-'])
    match = re.search(r'\{[^{}]*"input_i"[^{}]*\}', p.stderr, re.S)
    if match is None:
        raise RuntimeError('Unable to measure output loudness')
    obj = json.loads(match.group())
    return float(obj['input_i']), float(obj['input_tp'])


def render(audio: Path, ass: Path, output: Path) -> dict:
    a = ffprobe(audio)
    duration=float(a['format']['duration'])
    if duration <= 1:
        raise RuntimeError('Narration shorter than one second')
    ass_path=str(ass.resolve()).replace('\\','\\\\').replace(':','\\:').replace("'","\\'")
    run_cmd(['ffmpeg','-y','-hide_banner','-loglevel','error',
        '-f','lavfi','-i',f'color=c=0x101420:s=1920x1080:r=24:d={duration:.3f}',
        '-i',str(audio),'-vf',f"subtitles=filename='{ass_path}'",
        '-c:v','libx264','-preset','veryfast','-crf','23','-pix_fmt','yuv420p',
        '-c:a','aac','-b:a','160k','-ar','48000','-shortest',
        '-movflags','+faststart',str(output)])
    info=ffprobe(output)
    video=[s for s in info['streams'] if s['codec_type']=='video']
    audio_streams=[s for s in info['streams'] if s['codec_type']=='audio']
    if len(video)!=1 or len(audio_streams)!=1:
        raise RuntimeError('MP4 must have one video and one audio stream')
    if (video[0]['width'],video[0]['height'])!=(1920,1080):
        raise RuntimeError('Not Full HD')
    return info


def run(voice: Path, transcript: str, out: Path) -> dict:
    if not transcript.strip() or len(transcript)>1800:
        raise ValueError('Transcript must be nonempty and no longer than 1800 characters')
    out.mkdir(parents=True,exist_ok=True)
    if not voice.is_file() or not Path(str(voice)+'.json').is_file():
        raise FileNotFoundError('Piper voice .onnx and .onnx.json are both required')
    print('1/6 Piper WAV synthesis', flush=True)
    wav=PiperNarrator(voice).synthesize(transcript,out/'vo.wav')
    print('2/6 Two-pass EBU R128', flush=True)
    loud=normalize_loudness(Path(wav.wav_path),out/'vo_norm.wav')
    print('3/6 WhisperX CTC alignment', flush=True)
    aligned=WhisperXAligner(min_token_coverage=0.98).align(out/'vo_norm.wav',transcript)
    if aligned.method != 'whisperx_ctc':
        raise RuntimeError('Expected REAL WhisperX alignment, not interpolated timing')
    save_word_timestamps(aligned,out/'words.json')
    print('4/6 ASS captions and timing QA', flush=True)
    count,blocks=build_ass_from_words(aligned.words,out/'captions.ass',width=1920,height=1080)
    caption_qc=assess_caption_quality(aligned.words,blocks,aligned.duration_s,min_coverage=0.98)
    if not caption_qc.passed or caption_qc.text_match_ratio < 1:
        raise RuntimeError('Caption QC failed: '+str(caption_qc.failures))
    print('5/6 Render real 1080p MP4', flush=True)
    info=render(out/'vo_norm.wav',out/'captions.ass',out/'final.mp4')
    print('6/6 Final audio analysis and report', flush=True)
    final_lufs, final_tp=measure(out/'final.mp4')
    report={
       'source':'piper-tts-1.8.0 + whisperx-3.8.6-ctc',
       'transcript':transcript,
       'aligner_ran':True,
       'method':aligned.method,
       'token_coverage':aligned.token_coverage,
       'aligned_word_count':len(aligned.words),
       'caption_count':count,
       'caption_coverage':caption_qc.coverage_ratio,
       'caption_text_match':caption_qc.text_match_ratio,
       'final_duration_s':float(info['format']['duration']),
       'alignment_duration_s':aligned.duration_s,
       'normalized_lufs':loud.output_lufs,
       'final_lufs':final_lufs,
       'final_tp':final_tp,
       'resolution':'1920x1080',
    }
    (out/'qc_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report, indent=2), flush=True)
    return report


def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument('--voice',required=True,type=Path)
    p.add_argument('--transcript',required=True)
    p.add_argument('--output-dir',required=True,type=Path)
    args=p.parse_args()
    run(args.voice,args.transcript,args.output_dir)
    return 0

if __name__=='__main__':
    raise SystemExit(main())
