"""Finish the existing Task 7 browser demo with actual Task 8 CTC captions.

Run run_task7_demo.py with --piper-model first. No provider API, source queue,
editorial approval record or YouTube upload is created by this engineering demo.
"""
from __future__ import annotations
import argparse
import json
import shutil
from pathlib import Path
from narration_pro import WhisperXAligner, save_word_timestamps, build_ass_from_words, assess_caption_quality
from production_pro.demo import NARRATION
from production_pro.editing import burn_captions
from production_pro.qc import run_qc
from scripts.enforce_gates import enforce, measure_loudness


def run(work: Path, out: Path) -> dict:
    original=json.loads((work/'REPORT.json').read_text())
    if original['narrator']!='piper':
        raise ValueError('This integration demo requires actual Piper narration')
    out.mkdir(parents=True,exist_ok=True)
    shutil.copy2(work/'voice_raw.wav',out/'vo.wav')
    shutil.copy2(work/'voice_norm.wav',out/'vo_norm.wav')
    transcript=' '.join(NARRATION)
    aligned=WhisperXAligner(min_token_coverage=.98).align(out/'vo_norm.wav',transcript)
    save_word_timestamps(aligned,out/'words.json')
    count,blocks=build_ass_from_words(aligned.words,out/'captions.ass',width=1920,height=1080)
    captions=assess_caption_quality(aligned.words,blocks,aligned.duration_s)
    if not captions.passed:
        raise ValueError('Forced captions failed: '+str(captions.failures))
    burn_captions(work/'composed.mp4',out/'captions.ass',out/'final.mp4')
    qc=run_qc(out/'final.mp4',out/'captions.ass',forced_alignment_verified=aligned.method=='whisperx_ctc' and captions.passed)
    lufs,peak=measure_loudness(out/'final.mp4')
    report={'source':'real Chromium + Piper 1.8.0 + WhisperX 3.8.6 CTC',
            'transcript':transcript,'aligner_ran':True,'method':aligned.method,
            'token_coverage':aligned.token_coverage,'aligned_word_count':len(aligned.words),
            'caption_count':count,'final_lufs':lufs,'final_tp':peak,
            'final_duration_s':qc.duration_s,'alignment_duration_s':aligned.duration_s,
            'technical_qc':qc.model_dump(),'recording':original['recording'],
            'live_llm_tested':False,'owner_approved':False,'ready_for_publication':False}
    (out/'qc_report.json').write_text(json.dumps(report,indent=2))
    independent=enforce(out)
    (out/'independent_gates.json').write_text(json.dumps(independent,indent=2))
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--work',type=Path,default=Path('task7_demo_work'))
    parser.add_argument('--out',type=Path,default=Path('outputs/flowdesk-neural'))
    args=parser.parse_args()
    print(json.dumps(run(args.work,args.out),indent=2))
