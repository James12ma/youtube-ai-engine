"""Opt-in real neural voice and WhisperX CTC alignment proof.

Requires an explicitly supplied Piper .onnx model (+.onnx.json), installed
piper-tts==1.8.0 and whisperx==3.8.6, and pre-downloaded alignment model.
Does NOT download models or make an API call itself. No publishing.
"""
from __future__ import annotations
import argparse
import json
import subprocess
from pathlib import Path
from narration_pro import (PiperNarrator,WhisperXAligner,normalize_loudness,
                          build_ass_from_words,assess_caption_quality,save_word_timestamps)

DEMO_TEXT=("This is a demonstration of an original expense approval workflow. "
           "A manager reviews a travel expense and chooses whether to approve it. "
           "Every action shown comes from a functional local application.")

def run(model:Path, output_dir:Path, text:str=DEMO_TEXT)->dict:
    output_dir.mkdir(parents=True,exist_ok=True)
    synth=PiperNarrator(model).synthesize(text,output_dir/'neural_voice.wav')
    norm=normalize_loudness(Path(synth.wav_path),output_dir/'neural_voice_normalized.wav')
    aligned=WhisperXAligner().align(output_dir/'neural_voice_normalized.wav',text)
    save_word_timestamps(aligned,output_dir/'word_timestamps.json')
    count,blocks=build_ass_from_words(aligned.words,output_dir/'captions.ass',width=1920,height=1080)
    qc=assess_caption_quality(aligned.words,blocks,aligned.duration_s)
    if not qc.passed:
        raise RuntimeError("Caption quality gate failed: "+repr(qc.failures))
    ass_path=(output_dir/'captions.ass').resolve()
    # Use an original, clearly labeled demo background, not fabricated SaaS footage.
    vf="subtitles='"+str(ass_path).replace(':','\\:').replace("'","\\'")+"'"
    out=output_dir/'narration_alignment_demo.mp4'
    proc=subprocess.run(['ffmpeg','-y','-hide_banner','-loglevel','error',
        '-f','lavfi','-i',f'color=c=0x101420:s=1920x1080:d={aligned.duration_s:.3f}:r=24',
        '-i',str(output_dir/'neural_voice_normalized.wav'),'-vf',vf,
        '-c:v','libx264','-preset','veryfast','-crf','22','-pix_fmt','yuv420p',
        '-c:a','aac','-b:a','192k','-shortest','-movflags','+faststart',str(out)],
        capture_output=True,text=True)
    if proc.returncode:
        raise RuntimeError('MP4 render failed: '+proc.stderr[-400:])
    return dict(voice=synth.model_dump(),loudness=norm.model_dump(),alignment=dict(
                words=len(aligned.words),token_coverage=aligned.token_coverage,method=aligned.method),
                caption_quality=qc.model_dump(),captions=count,mp4=str(out))

if __name__=='__main__':
    p=argparse.ArgumentParser(description='Real neural voice + forced alignment, offline after model setup')
    p.add_argument('--model',type=Path,required=True,help='Absolute path to Piper ONNX voice file')
    p.add_argument('--output',type=Path,default=Path('task8_real_output'))
    args=p.parse_args()
    report=run(args.model,args.output)
    (args.output/'report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
