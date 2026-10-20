"""Render a sourced lesson with existing Piper, WhisperX, recorder and compositor.

This is an editorial draft, not a bypass of the owner's release approval gate.
"""
from __future__ import annotations
import argparse, json, shutil, subprocess, time, wave
from pathlib import Path
from narration_pro import PremadeNarrator,PiperOrEdgeNarrator,WhisperXAligner,normalize_loudness,save_word_timestamps,build_ass_from_words
from narration_pro.aligner import AlignmentResult, WordTimestamp, _tokens
from production_pro.recorder import WorkflowRecorder,focus_element
from production_pro.editing import compose_scenes,burn_captions
from production_pro.models import EditPlan
from production_pro.qc import run_qc
from scripts.render_showcase import export_srt
from scripts.build_practice_lab import build_lab,mount_lab
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


def phrase_time(words, phrase, start, end):
    flattened=[]
    for word in words:
        if word.start_s >= start-.05 and word.start_s < end:
            flattened.extend((token,word.start_s) for token in _tokens(word.word))
    expected=_tokens(phrase)
    for index in range(len(flattened)-len(expected)+1):
        if [x[0] for x in flattened[index:index+len(expected)]]==expected:return flattened[index][1]
    raise ValueError('Action cue absent from real aligned transcript: '+phrase)


def install_cursor(page):
    page.evaluate("""()=>{
      const style=document.createElement('style');style.textContent=`#capture-pointer{position:fixed;left:0;top:0;width:30px;height:38px;background:#fff;clip-path:polygon(0 0,0 90%,24% 68%,47% 100%,64% 91%,43% 60%,81% 57%);filter:drop-shadow(0 0 4px #000);z-index:1000;pointer-events:none;transform:translate(-80px,-80px)}.capture-click{position:fixed;width:56px;height:56px;border:4px solid #7bf1d0;border-radius:50%;z-index:999;pointer-events:none;animation:click-pulse .45s ease-out forwards}@keyframes click-pulse{to{transform:scale(1.8);opacity:0}}`;document.head.append(style);
      const cursor=document.createElement('div');cursor.id='capture-pointer';document.body.append(cursor);
      document.addEventListener('mousemove',event=>cursor.style.transform=`translate(${event.clientX}px,${event.clientY}px)`);
      document.addEventListener('mousedown',event=>{const ring=document.createElement('div');ring.className='capture-click';ring.style.left=(event.clientX-28)+'px';ring.style.top=(event.clientY-28)+'px';document.body.append(ring);setTimeout(()=>ring.remove(),500)});
    }""")


def lesson_chapters(sample=False):
    lesson=json.loads((LESSON/'lesson.json').read_text())
    indices=[0,3,4] if sample else list(range(len(lesson['chapters'])))
    return lesson, indices, [lesson['chapters'][i] for i in indices]


def run(voice,out,reuse=None,narration_dir=None,sample=False):
    out.mkdir(parents=True,exist_ok=True)
    lesson,chapter_indices,chapters=lesson_chapters(sample)
    transcript=' '.join(c['narration'] for c in chapters)
    if reuse:
        aligned=AlignmentResult.model_validate_json((reuse/'words.json').read_text())
        if aligned.transcript!=transcript or aligned.method!='whisperx_ctc':raise ValueError('Reuse transcript/alignment mismatch')
        old_report=json.loads((reuse/'qc_report.json').read_text())
        if old_report.get('narration_backend') not in ('piper','chatterbox'):raise ValueError('Expected verified Piper or Chatterbox narration')
        backend=old_report['narration_backend']
        timeline=old_report['chapters'];offset=aligned.duration_s;words=aligned.words
        subprocess.run(['ffmpeg','-y','-loglevel','error','-i',str(reuse/'final.mp4'),'-vn','-acodec','pcm_s16le',str(out/'vo.wav')],check=True)
        normalize_loudness(out/'vo.wav',out/'vo_norm.wav')
        save_word_timestamps(aligned,out/'words.json')
        if (reuse/'PIPER_MODEL_CARD.md').exists():shutil.copy2(reuse/'PIPER_MODEL_CARD.md',out/'PIPER_MODEL_CARD.md')
    else:
        # owner-approved shared voice (Chatterbox) when narrated beforehand; Piper otherwise
        narrator=PremadeNarrator(narration_dir) if narration_dir else PiperOrEdgeNarrator(voice,length_scale=1.03,noise_scale=.5,allow_edge_fallback=False)
        backend='chatterbox' if narration_dir else 'piper'
        aligner=WhisperXAligner(min_token_coverage=1)
        words=[];parts=[];timeline=[];offset=0
        for i,c in enumerate(chapters):
            path=out/f'voice_{i:02}.wav';narrator.synthesize(c['narration'],path)
            aligned=aligner.align(path,c['narration'])
            for word in aligned.words:words.append(WordTimestamp(**{**word.model_dump(),'start_s':word.start_s+offset,'end_s':word.end_s+offset}))
            timeline.append({'title':c['title'],'start':offset,'end':offset+aligned.duration_s})
            offset+=aligned.duration_s;parts.append(path)
            print(f'Chapter {i+1}: {backend} + WhisperX, {aligned.duration_s:.2f}s',flush=True)
        concat_wavs(parts,out/'vo.wav');normalize_loudness(out/'vo.wav',out/'vo_norm.wav')
        transcript=' '.join(c['narration'] for c in chapters)
        aligned=AlignmentResult(words=words,audio_path=str(out/'vo_norm.wav'),transcript=transcript,language='en',alignment_model='whisperx per-chapter CTC',duration_s=offset,token_coverage=1)
        save_word_timestamps(aligned,out/'words.json')
    clock={'start':None};evidence=[];steps=[]
    for position,(i,chapter,timing) in enumerate(zip(chapter_indices,chapters,timeline)):
        def show(page,c=chapter,t=timing,i=i,position=position):
            if clock['start'] is None:
                install_cursor(page);clock['start']=time.monotonic()
            page.evaluate("""({title,key,index,total,demo})=>{
              document.querySelector('#lesson-overlay')?.remove();
              const e=document.createElement('div');e.id='lesson-overlay';
              e.style.cssText=demo?'position:fixed;inset:0 0 auto;height:94px;background:#0b1021;z-index:50;padding:25px 62px;color:#73e9c9;font:bold 28px Arial;display:flex;justify-content:space-between':'position:fixed;inset:0;background:radial-gradient(ellipse at 80% 10%,#183d4a,#0b1021 65%);z-index:50;padding:105px 130px;color:#eef5ff;font-family:Arial';
              document.querySelector('#capture-pointer').style.opacity=demo?'1':'0';
              if(demo){e.textContent=`${String(index+1).padStart(2,'0')} / ${total}   •   ${title}`;}
              else{
                const brand=document.createElement('div');brand.textContent='LOGICSCRIPT  /  PRACTICAL AUTOMATION';brand.style.cssText='font-size:23px;letter-spacing:4px;color:#72e8c7;margin-bottom:55px';e.append(brand);
                const heading=document.createElement('h2');heading.textContent=title;heading.style.cssText='font-size:64px;line-height:1.15;max-width:1500px;margin:0 0 50px';e.append(heading);
                const line=document.createElement('div');line.textContent=key;line.style.cssText='font-size:54px;line-height:1.4;color:#7bf1d0;border-left:7px solid #7bf1d0;padding:28px 40px;background:#14273b;max-width:1600px';e.append(line);
                const lower=document.createElement('div');lower.id='lesson-detail';lower.style.cssText='font-size:30px;color:#aebed8;margin-top:54px';lower.textContent='Observe → predict → test → compare';e.append(lower);
                const note=document.createElement('div');note.textContent=`${String(index+1).padStart(2,'0')} / ${total}   •   ORIGINAL EDUCATIONAL DEMONSTRATION`;note.style.cssText='position:absolute;bottom:190px;font-size:20px;letter-spacing:3px;color:#7c91b2';e.append(note);
              }
              e.animate([{opacity:0,transform:'translateY(14px)'},{opacity:1,transform:'translateY(0px)'}],{duration:250,fill:'both'});document.body.append(e);
            }""",{'title':c['title'],'key':c['key'],'index':position,'total':len(chapters),'demo':bool(c['demo']) or bool(c.get('lab')) or i==0})
            if i==0:
                # Cold open: demonstrate the actual boundary before the explanation.
                def hook_move(selector):
                    box=page.locator(selector).bounding_box();page.mouse.move(box['x']+box['width']/2,box['y']+box['height']/2,steps=10)
                hook_move('#amount');page.locator('#amount').click();page.locator('#amount').press_sequentially('100',delay=80)
                hook_move('#category');page.locator('#category').select_option('travel')
                hook_move('#submit');page.locator('#submit').click()
                assert 'AUTO-APPROVED' in page.locator('#result').inner_text()
                first_result=page.locator('#result').inner_text()
                hook_move('#amount');page.locator('#amount').click();page.locator('#amount').press('ControlOrMeta+A');page.locator('#amount').press_sequentially('100.01',delay=80)
                target=phrase_time(words,'just one cent',t['start'],t['end'])
                remaining=target-.4-(time.monotonic()-clock['start'])
                if remaining>0:page.wait_for_timeout(remaining*1000)
                hook_move('#submit');page.locator('#submit').click();actual=time.monotonic()-clock['start']
                observed=page.locator('#result').inner_text();assert 'SENT FOR MANAGER REVIEW' in observed
                focus_element(page,'#result');hook_move('#result')
                evidence.append({'chapter':'Cold open — actual boundary pair','amount':'100.01','category':'travel','expected':'SENT FOR MANAGER REVIEW','observed':observed,'prior_observed':first_result,'passed':True,'spoken_click_cue_s':target,'actual_click_s':actual,'sync_error_s':actual-target})
            elif c.get('lab'):
                if not page.locator('#practice-lab').count():
                    mount_lab(page)
                page.locator('#capture-pointer').evaluate("el=>el.style.opacity='1'")
                def lab_click(selector,phrase):
                    target=phrase_time(words,phrase,t['start'],t['end'])
                    remaining=target-.2-(time.monotonic()-clock['start'])
                    if remaining>0:page.wait_for_timeout(remaining*1000)
                    box=page.locator(selector).bounding_box();page.mouse.move(box['x']+box['width']/2,box['y']+box['height']/2,steps=10)
                    page.locator(selector).click();actual=time.monotonic()-clock['start']
                    evidence.append({'chapter':c['title'],'action':selector,'passed':True,'spoken_click_cue_s':target,'actual_click_s':actual,'sync_error_s':actual-target})
                if c['lab']=='guide':
                    lab_click('#download','click Save practice file')
                elif c['lab']=='matrix':
                    lab_click('#matrix-tab','Select Test matrix')
                    lab_click('#run','Click Run all cases')
                    assert page.locator('#summary').inner_text().startswith('11 passed / 0 failed')
                    evidence[-1]['observed']=page.locator('#summary').inner_text()
                else:
                    lab_click('#mutate','Click Introduce wrong expectation')
                    lab_click('#run','Click Run all cases again')
                    assert page.locator('#summary').inner_text().startswith('10 passed / 1 failed')
                    evidence[-1]['observed']=page.locator('#summary').inner_text()
                    lab_click('#mutate','click Restore correct expectation')
                    lab_click('#run','then run the cases again')
                    assert page.locator('#summary').inner_text().startswith('11 passed / 0 failed')
                    evidence[-1]['observed']=page.locator('#summary').inner_text()
            elif c['demo']:
                amount,category,expected=c['demo']
                cues={3:'Now we run the rule',4:'Run the rule again',5:'so the boundary is approved',6:'Run the rule',7:'so this request is automatically approved',8:'so sixty needs review',9:'Run the rule'}
                click_at=phrase_time(words,cues[i],t['start'],t['end'])
                def wait_until(target):
                    remaining=target-(time.monotonic()-clock['start'])
                    if remaining>0:page.wait_for_timeout(remaining*1000)
                def move_to(selector):
                    box=page.locator(selector).bounding_box()
                    if not box:raise ValueError('Missing visible action target')
                    page.mouse.move(box['x']+box['width']/2,box['y']+box['height']/2,steps=10)
                    page.wait_for_timeout(70)
                wait_until(t['start']+(.10 if i!=3 else 2.0))
                focus_element(page,'#amount');move_to('#amount');page.locator('#amount').click()
                page.locator('#amount').press('ControlOrMeta+A');page.locator('#amount').press_sequentially(amount,delay=95)
                if page.locator('#category').input_value()!=category or i==3:
                    move_to('#category');page.locator('#category').click()
                    page.locator('#category').press('Escape')
                    page.locator('#category').evaluate('el=>el.size=4')
                    move_to('#category option[value="'+category+'"]')
                    page.locator('#category').select_option(category);page.wait_for_timeout(250)
                    page.locator('#category').evaluate('el=>el.size=1')
                # Let the focus transition settle before the spoken click cue.
                focus_element(page,'#submit');wait_until(click_at-.5)
                move_to('#submit');page.locator('#submit').click()
                actual_time=time.monotonic()-clock['start']
                observed=page.locator('#result').inner_text();assert expected in observed,(expected,observed)
                focus_element(page,'#result');move_to('#result')
                evidence.append({'chapter':c['title'],'amount':amount,'category':category,'expected':expected,'observed':observed,'passed':True,'spoken_click_cue_s':click_at,'actual_click_s':actual_time,'sync_error_s':actual_time-click_at})
            else:
                # Reveal distinct teaching details during continuous narration.
                details={0:['Boundary: $100.00 approved','$100.01 needs review'],1:['Travel ≤ $100  |  Software ≤ $200','Supplies ≤ $50  |  Invalid → reject'],2:['Validity is not permission','A policy decision does not move money'],10:['Travel: 100.00 / 100.01','Software: 200.00 / 200.01   •   Supplies: 50.00 / 50.01'],11:['Binary floats approximate decimal fractions','Choose explicit precision and rounding'],12:['Repeat validation on the server','Deny by default • Check every request'],13:['No authentication, database or payments','Test those controls before connecting accounts'],14:['Test both sides of each boundary','Keep the matrix and a decision record']}
                for n,detail in enumerate(details.get(14 if i==len(chapters)-1 else i,['Inspect the policy','Compare expected and observed results'])):
                    target=t['start']+(n+1)*(t['end']-t['start'])/3
                    remaining=target-(time.monotonic()-clock['start'])
                    if remaining>0:page.wait_for_timeout(remaining*1000)
                    page.locator('#lesson-detail').evaluate("(el,text)=>{el.textContent=text;el.animate([{opacity:0,transform:'translateX(20px)'},{opacity:1,transform:'translateX(0)'}],{duration:220,fill:'both'})}",detail)
            remaining=t['end']-(time.monotonic()-clock['start'])
            if remaining>0:page.wait_for_timeout(remaining*1000)
        steps.append((chapter['title'],show))
    capture=WorkflowRecorder('local-inline-demo',out/'capture',viewport=(1920,1080),initial_wait_ms=180,chapter_pause_ms=0).record(steps)
    (out/'demo_evidence.json').write_text(json.dumps(evidence,indent=2))
    if any(abs(row['sync_error_s'])>.9 for row in evidence):raise RuntimeError('Spoken action timing exceeds 0.9s review threshold')
    lead=max(0,capture.duration_s-capture.chapters[-1].end_s)
    compose_scenes([EditPlan(scene_index=0,source_path=capture.video_path,start_s=lead,duration_s=offset,overlap_s=0)],out/'vo_norm.wav',out/'uncaptioned.mp4',width=1920,height=1080,fps=24,workdir=out/'edits')
    count,_=build_ass_from_words(words,out/'captions.ass',width=1920,height=1080,animated=True,size=48,max_chars_per_line=32,max_duration_s=2.8,bottom_margin=65)
    burn_captions(out/'uncaptioned.mp4',out/'captions.ass',out/'final.mp4');export_srt(out/'captions.ass',out/'captions.srt')
    qc=run_qc(out/'final.mp4',out/'captions.ass',min_caption_coverage=.70,forced_alignment_verified=True)
    if not qc.passed:raise RuntimeError('Technical QC failed; inspect report')
    lufs,peak=measure_loudness(out/'final.mp4')
    report={'title':lesson['title'],'transcript':transcript,'provenance':lesson['provenance'],'aligner_ran':True,'method':'whisperx_ctc','token_coverage':1,'narration_backend':backend,'aligned_word_count':len(words),'caption_count':count,'final_duration_s':qc.duration_s,'alignment_duration_s':offset,'final_lufs':lufs,'final_tp':peak,'technical_qc':qc.model_dump(),'resolution':'1920x1080','ready_for_publication':False,'publishing':'disabled','live_llm_calls':0,'editorial_review':'separate review required','chapters':timeline}
    (out/'qc_report.json').write_text(json.dumps(report,indent=2))
    gates=enforce(out,expected_size=(1920,1080));(out/'independent_gates.json').write_text(json.dumps(gates,indent=2))
    (out/'demo_evidence.json').write_text(json.dumps(evidence,indent=2))
    (out/'LogicScript_Practice_Lab.html').write_text(build_lab())
    for file in ('script.md','sources.md','lesson.json','test-matrix.csv'):shutil.copy2(LESSON/file,out/file)
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
    parser=argparse.ArgumentParser();parser.add_argument('--voice',type=Path);parser.add_argument('--output-dir',type=Path,default=Path('outputs/educational'))
    parser.add_argument('--reuse-narration',type=Path)
    parser.add_argument('--narration-dir',type=Path,help='premade narration (scripts/narrate_texts.py)')
    parser.add_argument('--dump-texts',type=Path,help='write the texts to narrate as JSON and exit')
    parser.add_argument('--sample',action='store_true',help='Render three original action chapters as a short private engine test')
    args=parser.parse_args()
    if args.dump_texts:
        args.dump_texts.write_text(json.dumps([c['narration'] for c in lesson_chapters(args.sample)[2]],ensure_ascii=False));raise SystemExit(0)
    run(args.voice,args.output_dir,args.reuse_narration,args.narration_dir,args.sample)
