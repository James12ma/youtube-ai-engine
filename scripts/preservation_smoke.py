"""Real interaction/footage proofs with offline ENGINEERING voice, never a final release.

The explicitly selected eSpeak path does not invoke ONNX, cloud speech or an
alignment model. Sentence WAV boundaries are measured; word captions are
approximate and labelled as such. Neural narration remains a separate gate.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import subprocess
import time
import wave
from pathlib import Path

from production_pro.models import NarrationResult, NarrationSegment, EditPlan
from production_pro.captions import write_captions
from production_pro.lesson_narration import concat_wavs
from production_pro.premium import QualityProfile, master_video, audit_video
from production_pro.editing import compose_scenes


def engineering_voice(texts, out: Path, language: str):
    out.mkdir(parents=True, exist_ok=True)
    segments=[]
    for i, text in enumerate(texts):
        wav=out/f'{i:02}.wav'
        subprocess.run(['espeak','-v','en-us' if language=='en' else 'es','-s','145',
                        '-w',str(wav),text],check=True,capture_output=True)
        with wave.open(str(wav),'rb') as stream:
            duration=stream.getnframes()/stream.getframerate()
        segments.append(NarrationSegment(text=text,audio_path=str(wav),duration_s=duration))
    result=NarrationResult(segments=segments,total_duration_s=sum(s.duration_s for s in segments),
                           backend='espeak-engineering-only')
    concat_wavs([Path(s.audio_path) for s in segments],out/'voice.wav')
    write_captions(result,out/'captions.ass',1920,1080)
    return result


def watermark(src: Path, out: Path):
    label=out.parent/'engineering_label.txt'
    label.write_text('ENGINEERING PROOF | robotic test voice | NOT FOR PUBLICATION')
    subprocess.run(['ffmpeg','-y','-v','error','-i',str(src),'-vf',
                    f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:textfile='{label.resolve()}':"
                    'fontsize=24:fontcolor=white:x=(w-tw)/2:y=20:box=1:boxcolor=black@0.7:boxborderw=10',
                    '-an','-c:v','libx264','-preset','veryfast','-crf','20',str(out)],check=True)


def screen(out: Path):
    from production_pro.sheet_recorder import SheetRecorder
    template=Path('content/expense-tracker-lesson/LogicScript_Expense_Tracker.xlsx')
    before=hashlib.sha256(template.read_bytes()).hexdigest()
    texts=[
        'This is a real spreadsheet in LibreOffice Calc. The file also opens in Excel. Watch the cursor move and click the sheet.',
        'I type the number forty one point twenty five and press Enter. The sheet accepts a numeric amount.',
        'Now I import an amount stored as text. Direct imports can bypass input validation. The live formula flags ERROR.',
        'I fix the imported text by typing thirty eight point seventy five. Press Enter. The status changes back to OK.',
        'Here is a real category menu. I open the list and close it. Next, the Format menu opens above the sheet.',
        'I scroll down through the expense rows, then return to the summary. The workbook calculates the results itself.',
        'The summary says ALL CHECKS PASSED. This proves the workflow. The robotic voice is for engineering review only.'
    ]
    narration=engineering_voice(texts,out/'speech','en')
    starts=[];t=0
    for seg in narration.segments: starts.append(t);t+=seg.duration_s
    setup=json.loads(Path('content/expense-tracker-lesson/lesson.json').read_text())['demo_setup']
    actions=[
        (0.7,{'do':'move','x':850,'y':345}),
        (1.5,{'do':'click'}),
        (starts[1]+.7,{'do':'type','ref':'Expenses!E9','text':'41.25','expect':{'Expenses!E9':'41.25','Expenses!J9':'OK'}}),
        (starts[2]+.7,{'do':'set','ref':'Expenses!E9','value':'$38.75','expect':{'Expenses!E9':'$38.75','Expenses!J9':'ERROR','Expenses!K9':'Amount is not a number.'}}),
        (starts[3]+.7,{'do':'type','ref':'Expenses!E9','text':'38.75','expect':{'Expenses!E9':'38.75','Expenses!J9':'OK'}}),
        (starts[4]+.3,{'do':'select','ref':'Expenses!D9'}),
        (starts[4]+1,{'do':'key','keys':'alt+Down'}),
        (starts[4]+3,{'do':'key','keys':'Escape'}),
        (starts[4]+4,{'do':'menu','keys':'alt+o'}),
        (starts[4]+6,{'do':'key','keys':'Escape'}),
        (starts[5]+.4,{'do':'move','x':900,'y':550}),
        (starts[5]+1,{'do':'scroll','direction':'down','count':9}),
        (starts[5]+4,{'do':'select','ref':'Summary!A1'}),
        (starts[6]+.4,{'do':'select','ref':'Summary!B4','expect':{'Summary!B4':'ALL CHECKS PASSED'}})
    ]
    with SheetRecorder(template,out/'capture',zoom=110) as rec:
        rec.apply({'do':'clear','ref':setup['clear']},sleep=lambda s:None)
        for a in setup['rows']:rec.apply(a,sleep=lambda s:None)
        rec.apply({'do':'row','row':9,'values':[{'date':'2026-01-28'},'Corner cafe','Client lunch','Meals',38.75,'Card','Yes','','']},sleep=lambda s:None)
        rec.apply({'do':'select','ref':'Expenses!A6'})
        rec.snapshot(out/'capture'/'initial.png')
        captured=rec.record(actions,narration.total_duration_s+.4,out/'capture'/'raw.mp4',
                            evidence_refs=lambda a:list(a.get('expect',{})))
    (out/'actions.json').write_text(json.dumps(captured.log,indent=2))
    failures=[(ref,want,a.get('observed',{}).get(ref)) for a in captured.log
              for ref,want in a['action'].get('expect',{}).items() if a.get('observed',{}).get(ref)!=want]
    if failures:raise RuntimeError('Actual workbook mismatch: '+repr(failures))
    if hashlib.sha256(template.read_bytes()).hexdigest()!=before:raise RuntimeError('Source template changed')
    # Keep the actual recording at normal speed; no mock UI or frozen replacements.
    compose_scenes([EditPlan(scene_index=0,source_path=str(captured.video_path),start_s=captured.lead_s,
                             duration_s=narration.total_duration_s)],out/'speech'/'voice.wav',out/'timed.mp4',
                   width=1920,height=1080,fps=24,workdir=out/'edit')
    watermark(out/'timed.mp4',out/'picture.mp4')
    profile=QualityProfile('screen','en')
    mastered=master_video(out/'picture.mp4',out/'speech'/'voice.wav',out/'LogicScript_Screen_Proof.mp4',
                          profile=profile,captions=out/'speech'/'captions.ass')
    report=audit_video(out/'LogicScript_Screen_Proof.mp4',profile=profile,screen_actions=captured.log)
    report.update(actions=captured.log,source_template_sha256=before,template_unchanged=True,
                  narration_backend=narration.backend,caption_alignment='approximate word timing; measured sentence WAV boundaries',
                  professional_voice_verified=False,mastering=mastered)
    (out/'report.json').write_text(json.dumps(report,indent=2))
    assert report['technical_passed'] and report['mode_evidence']['passed']
    return report


def documentary(out: Path, footage: Path):
    from channel.documentary import Shot, _cut_shot, _xfade_chain
    from channel.noaa import info
    texts=[
        'Una ballena jorobada se acerca bajo el agua. En estas imágenes de NOAA vemos su cuerpo y sus aletas.',
        'La cámara sigue a la ballena mientras gira. Son imágenes de archivo, no una familia seguida durante un mismo viaje.',
        'Esta muestra comprueba los cortes, las transiciones, los subtítulos y el sonido. La voz de prueba todavía no es la voz final.'
    ]
    narration=engineering_voice(texts,out/'speech','es')
    parts=[];seconds=[];shots=[];fade=.4
    for i,seg in enumerate(narration.segments):
        p=out/f'shot_{i}.mp4'
        start=(119.5,28,94)[i]
        length=seg.duration_s+(fade if i<len(texts)-1 else 0)
        _cut_shot(footage,Shot(clip='whales',in_s=start,out_s=start+length+1),length,p,out,i,
                  width=1920,height=1080,fps=24,label='Archivo NOAA Fisheries | Banco de la Plata',disclosure='')
        parts.append(p);seconds.append(seg.duration_s)
        shots.append({'clip':'whales','source_in_s':start,'seconds':seg.duration_s})
    _xfade_chain(parts,seconds,fade,out/'edited.mp4',24)
    watermark(out/'edited.mp4',out/'picture.mp4')
    profile=QualityProfile('documentary','es')
    mastered=master_video(out/'picture.mp4',out/'speech'/'voice.wav',out/'Alan7_Documentary_Proof.mp4',
                          profile=profile,captions=out/'speech'/'captions.ass')
    report=audit_video(out/'Alan7_Documentary_Proof.mp4',profile=profile,
                        documentary_report={'shots':shots,'license_gate':{'review_pending':True}})
    report.update(narration_backend=narration.backend,caption_alignment='approximate word timing; measured sentence WAV boundaries',
                  professional_voice_verified=False,original_neural_documentary_e2e='NOT RUN: separate narration authorization needed',
                  footage_source=info(3911325489001),source_resolution='1280x720 (upscaled by existing shot renderer)',
                  shots=shots,mastering=mastered)
    (out/'report.json').write_text(json.dumps(report,indent=2))
    assert report['technical_passed']
    return report


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mode',choices=('screen','documentary'),required=True)
    p.add_argument('--output-dir',type=Path,required=True)
    p.add_argument('--footage',type=Path)
    p.add_argument('--engineering-voice',action='store_true',required=True)
    a=p.parse_args(argv);a.output_dir.mkdir(parents=True,exist_ok=True)
    if a.mode=='documentary' and not a.footage:p.error('Documentary needs an explicit local footage file')
    report=screen(a.output_dir) if a.mode=='screen' else documentary(a.output_dir,a.footage)
    print(json.dumps({k:report[k] for k in ('mode','technical_passed','duration_s','mode_evidence','ready_for_publication')},indent=2))


if __name__=='__main__':main()
