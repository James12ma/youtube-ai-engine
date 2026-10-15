"""Render a sourced lesson with existing Piper, WhisperX, recorder and compositor.

This is an editorial draft, not a bypass of the owner's release approval gate.
"""
from __future__ import annotations
import argparse, json, shutil, subprocess, time, wave
from pathlib import Path
from narration_pro import PiperOrEdgeNarrator,WhisperXAligner,normalize_loudness,save_word_timestamps,build_ass_from_words
from narration_pro.aligner import AlignmentResult, WordTimestamp
from production_pro.recorder import WorkflowRecorder,focus_element
from production_pro.editing import compose_scenes,burn_captions
from production_pro.models import EditPlan
from production_pro.qc import run_qc
from scripts.render_showcase import export_srt
from scripts.enforce_gates import enforce,measure_loudness

ROOT=Path(__file__).resolve().parents[1]
LESSON=ROOT/'content/expense-rule-lesson'


def concat_wavs(paths,out):
    with wave.open(str(out),'wb') as dest:
        for i,path in enumerate(paths):
            with wave.open(str(path),'rb') as src:
                if i==0:params=src.getparams();dest.setparams(params)
                elif src.getparams()[:4]!=params[:4]:
                    # Frame count differs; compare only audio format fields.
                    if src.getparams()[:3]!=params[:3]:raise ValueError('Inconsistent voice format')
                dest.writeframes(src.readframes(src.getnframes()))


def run(voice,out):
    out.mkdir(parents=True,exist_ok=True)
    lesson=json.loads((LESSON/'lesson.json').read_text());chapters=lesson['chapters']
    narrator=PiperOrEdgeNarrator(voice,length_scale=1.03,noise_scale=.5,allow_edge_fallback=False)
    aligner=WhisperXAligner(min_token_coverage=1)
    words=[];parts=[];timeline=[];offset=0
    for i,c in enumerate(chapters):
        path=out/f'voice_{i:02}.wav';narrator.synthesize(c['narration'],path)
        aligned=aligner.align(path,c['narration'])
        for word in aligned.words:words.append(WordTimestamp(**{**word.model_dump(),'start_s':word.start_s+offset,'end_s':word.end_s+offset}))
        timeline.append({'title':c['title'],'start':offset,'end':offset+aligned.duration_s})
        offset+=aligned.duration_s;parts.append(path)
        print(f'Chapter {i+1}: real Piper + WhisperX, {aligned.duration_s:.2f}s',flush=True)
    concat_wavs(parts,out/'vo.wav');normalize_loudness(out/'vo.wav',out/'vo_norm.wav')
    transcript=' '.join(c['narration'] for c in chapters)
    aligned=AlignmentResult(words=words,audio_path=str(out/'vo_norm.wav'),transcript=transcript,language='en',alignment_model='whisperx per-chapter CTC',duration_s=offset,token_coverage=1)
    save_word_timestamps(aligned,out/'words.json')
    clock={'start':None};evidence=[];steps=[]
    for i,(chapter,timing) in enumerate(zip(chapters,timeline)):
        def show(page,c=chapter,t=timing,i=i):
            if clock['start'] is None:clock['start']=time.monotonic()
            page.evaluate("""({title,key,index,total,demo})=>{
              document.querySelector('#lesson-overlay')?.remove();
              const e=document.createElement('div');e.id='lesson-overlay';
              e.style.cssText=demo?'position:fixed;inset:0 0 auto;height:94px;background:#0b1021;z-index:50;padding:25px 62px;color:#73e9c9;font:bold 28px Arial;display:flex;justify-content:space-between':'position:fixed;inset:0;background:radial-gradient(ellipse at 80% 10%,#183d4a,#0b1021 65%);z-index:50;padding:105px 130px;color:#eef5ff;font-family:Arial';
              if(demo){e.textContent=`${String(index+1).padStart(2,'0')} / ${total}   •   ${title}`;}
              else{
                const brand=document.createElement('div');brand.textContent='LOGICSCRIPT  /  PRACTICAL AUTOMATION';brand.style.cssText='font-size:23px;letter-spacing:4px;color:#72e8c7;margin-bottom:55px';e.append(brand);
                const heading=document.createElement('h2');heading.textContent=title;heading.style.cssText='font-size:64px;line-height:1.15;max-width:1500px;margin:0 0 50px';e.append(heading);
                const line=document.createElement('div');line.textContent=key;line.style.cssText='font-size:54px;line-height:1.4;color:#7bf1d0;border-left:7px solid #7bf1d0;padding:28px 40px;background:#14273b;max-width:1600px';e.append(line);
                const lower=document.createElement('div');lower.id='lesson-detail';lower.style.cssText='font-size:30px;color:#aebed8;margin-top:54px';lower.textContent='Observe → predict → test → compare';e.append(lower);
                const note=document.createElement('div');note.textContent=`${String(index+1).padStart(2,'0')} / ${total}   •   ORIGINAL EDUCATIONAL DEMONSTRATION`;note.style.cssText='position:absolute;bottom:190px;font-size:20px;letter-spacing:3px;color:#7c91b2';e.append(note);
              }
              e.animate([{opacity:0,transform:'translateY(14px)'},{opacity:1,transform:'translateY(0px)'}],{duration:250,fill:'both'});document.body.append(e);
            }""",{'title':c['title'],'key':c['key'],'index':i,'total':len(chapters),'demo':bool(c['demo'])})
            if c['demo']:
                amount,category,expected=c['demo']
                focus_element(page,'#amount');page.locator('#amount').fill(amount)
                page.locator('#category').select_option(category)
                page.wait_for_timeout(1800)
                focus_element(page,'#submit');page.locator('#submit').click()
                observed=page.locator('#result').inner_text();assert expected in observed,(expected,observed)
                focus_element(page,'#result');evidence.append({'chapter':c['title'],'amount':amount,'category':category,'expected':expected,'observed':observed,'passed':True})
            else:
                page.wait_for_timeout(5000)
                page.locator('#lesson-detail').evaluate("el=>el.textContent='One-cent boundary pair: 100.00 → approve   /   100.01 → review'") if i in (0,10,14) else None
            remaining=t['end']-(time.monotonic()-clock['start'])
            if remaining>0:page.wait_for_timeout(remaining*1000)
        steps.append((chapter['title'],show))
    capture=WorkflowRecorder('local-inline-demo',out/'capture',viewport=(1920,1080),initial_wait_ms=180,chapter_pause_ms=0).record(steps)
    lead=max(0,capture.duration_s-capture.chapters[-1].end_s)
    compose_scenes([EditPlan(scene_index=0,source_path=capture.video_path,start_s=lead,duration_s=offset,overlap_s=0)],out/'vo_norm.wav',out/'uncaptioned.mp4',width=1920,height=1080,fps=24,workdir=out/'edits')
    count,_=build_ass_from_words(words,out/'captions.ass',width=1920,height=1080,animated=True,size=48,max_chars_per_line=32,max_duration_s=2.8,bottom_margin=65)
    burn_captions(out/'uncaptioned.mp4',out/'captions.ass',out/'final.mp4');export_srt(out/'captions.ass',out/'captions.srt')
    qc=run_qc(out/'final.mp4',out/'captions.ass',min_caption_coverage=.70,forced_alignment_verified=True)
    if not qc.passed:raise RuntimeError('Technical QC failed; inspect report')
    lufs,peak=measure_loudness(out/'final.mp4')
    report={'title':lesson['title'],'transcript':transcript,'provenance':lesson['provenance'],'aligner_ran':True,'method':'whisperx_ctc','token_coverage':1,'narration_backend':'piper','aligned_word_count':len(words),'caption_count':count,'final_duration_s':qc.duration_s,'alignment_duration_s':offset,'final_lufs':lufs,'final_tp':peak,'technical_qc':qc.model_dump(),'resolution':'1920x1080','ready_for_publication':False,'publishing':'disabled','live_llm_calls':0,'editorial_review':'separate review required','chapters':timeline}
    (out/'qc_report.json').write_text(json.dumps(report,indent=2))
    gates=enforce(out,expected_size=(1920,1080));(out/'independent_gates.json').write_text(json.dumps(gates,indent=2))
    (out/'demo_evidence.json').write_text(json.dumps(evidence,indent=2))
    for file in ('script.md','sources.md','lesson.json'):shutil.copy2(LESSON/file,out/file)
    frames=out/'review_frames';frames.mkdir(exist_ok=True)
    for i,t in enumerate(timeline):
        subprocess.run(['ffmpeg','-y','-loglevel','error','-ss',str(t['start']+min(8,(t['end']-t['start'])/2)),'-i',str(out/'final.mp4'),'-frames:v','1',str(frames/f'{i:02}.jpg')],check=True)
    from PIL import Image,ImageDraw,ImageFont
    image=Image.new('RGB',(1280,720),'#0b1021');draw=ImageDraw.Draw(image)
    font='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
    draw.text((70,65),'LOGICSCRIPT',fill='#7bf1d0',font=ImageFont.truetype(font,32))
    draw.text((70,170),'THE ONE-CENT',fill='white',font=ImageFont.truetype(font,79))
    draw.text((70,270),'BOUNDARY TEST',fill='white',font=ImageFont.truetype(font,79))
    draw.rounded_rectangle((70,430,1210,610),22,fill='#17354a')
    draw.text((110,475),'$100.00',fill='#7bf1d0',font=ImageFont.truetype(font,65))
    draw.text((680,475),'$100.01',fill='#f7bf75',font=ImageFont.truetype(font,65))
    image.save(out/'thumbnail.jpg',quality=95)
    print(json.dumps({'duration':offset,'qc':qc.model_dump(),'gates':gates},indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--voice',type=Path,required=True);parser.add_argument('--output-dir',type=Path,default=Path('outputs/educational'))
    args=parser.parse_args();run(args.voice,args.output_dir)
