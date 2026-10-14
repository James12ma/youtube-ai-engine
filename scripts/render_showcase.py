"""Real neural, action-paced original demo in landscape and portrait. Never uploads."""
from __future__ import annotations
import argparse,json,shutil,time,subprocess
from pathlib import Path
from narration_pro import PiperNarrator,WhisperXAligner,normalize_loudness,save_word_timestamps,build_ass_from_words
from narration_pro.aligner import _tokens
from production_pro.recorder import WorkflowRecorder,focus_element
from production_pro.editing import compose_scenes,burn_captions
from production_pro.models import EditPlan
from production_pro.qc import run_qc
from scripts.enforce_gates import enforce,measure_loudness

SENTENCES=[
    'One rule. Two outcomes. Watch this original expense approval demo.',
    'Enter one hundred twenty dollars, then choose travel.',
    'Run the rule. This amount needs manager review.',
    'Now lower the amount to eighty dollars and run it again.',
    'Auto approved. Test both outcomes before connecting real business accounts.'
]
FORMATS={'landscape':(1920,1080),'portrait':(1080,1920)}


def sentence_boundaries(aligned):
    expected=_tokens(' '.join(SENTENCES))
    actual=_tokens(' '.join(w.word for w in aligned.words))
    if actual!=expected:raise ValueError('Full ordered transcript required to pace browser actions')
    counts=[];count=0
    for word in aligned.words:
        count+=len(_tokens(word.word));counts.append(count)
    ends=[];count=0
    for sentence in SENTENCES:
        count+=len(_tokens(sentence))
        idx=counts.index(count)
        ends.append(aligned.words[idx].end_s)
    return [0.0,*ends[:-1],aligned.duration_s]


def paced_steps(boundaries):
    clock={'start':None}
    def overview(page):
        page.locator('h1').evaluate("el => el.textContent='One rule. Two outcomes.'")
    def enter(page):
        focus_element(page,'#amount');page.locator('#amount').fill('')
        page.locator('#amount').press_sequentially('120',delay=65)
        page.locator('#category').select_option('travel')
    def review(page):
        focus_element(page,'#submit');page.locator('#submit').click()
        assert 'SENT FOR MANAGER REVIEW' in page.locator('#result').inner_text()
        focus_element(page,'#result')
    def lower(page):
        focus_element(page,'#amount');page.locator('#amount').fill('80')
        page.locator('#submit').click()
        assert 'AUTO-APPROVED' in page.locator('#result').inner_text()
    def finish(page):focus_element(page,'#result')
    steps=[]
    for i,action in enumerate([overview,enter,review,lower,finish]):
        def timed(page,action=action,end=boundaries[i+1]):
            if clock['start'] is None:clock['start']=time.monotonic()
            action(page)
            remaining=end-(time.monotonic()-clock['start'])
            if remaining>0:page.wait_for_timeout(remaining*1000)
        steps.append((SENTENCES[i],timed))
    return steps


def run(voice:Path,out:Path,formats:list[str]):
    out.mkdir(parents=True,exist_ok=True)
    shared=out/'narration';shared.mkdir(exist_ok=True)
    transcript=' '.join(SENTENCES)
    speech=PiperNarrator(voice,length_scale=.96,noise_scale=.55).synthesize(transcript,shared/'vo.wav')
    normalize_loudness(Path(speech.wav_path),shared/'vo_norm.wav')
    aligned=WhisperXAligner(min_token_coverage=1).align(shared/'vo_norm.wav',transcript)
    save_word_timestamps(aligned,shared/'words.json')
    boundaries=sentence_boundaries(aligned)
    reports={}
    for name in formats:
        width,height=FORMATS[name];folder=out/name;folder.mkdir(exist_ok=True)
        for file in ['vo.wav','vo_norm.wav','words.json']:shutil.copy2(shared/file,folder/file)
        capture=WorkflowRecorder('local-inline-demo',folder/'capture',viewport=(width,height),
            initial_wait_ms=180,chapter_pause_ms=0).record(paced_steps(boundaries))
        lead=max(0,capture.duration_s-capture.chapters[-1].end_s)
        compose_scenes([EditPlan(scene_index=0,source_path=capture.video_path,start_s=lead,
            duration_s=aligned.duration_s,overlap_s=0)],folder/'vo_norm.wav',folder/'uncaptioned.mp4',
            width=width,height=height,fps=24,workdir=folder/'edits')
        count,_=build_ass_from_words(aligned.words,folder/'captions.ass',width=width,height=height,
            animated=True,size=66 if name=='portrait' else 54,max_chars_per_line=24 if name=='portrait' else 32,
            max_duration_s=2.4,bottom_margin=300 if name=='portrait' else 80)
        burn_captions(folder/'uncaptioned.mp4',folder/'captions.ass',folder/'final.mp4')
        qc=run_qc(folder/'final.mp4',folder/'captions.ass',min_caption_coverage=.70,forced_alignment_verified=True)
        lufs,peak=measure_loudness(folder/'final.mp4')
        report={'transcript':transcript,'aligner_ran':True,'method':aligned.method,
            'token_coverage':aligned.token_coverage,'aligned_word_count':len(aligned.words),
            'caption_count':count,'caption_animation':'WhisperX-timed ASS karaoke sweep',
            'final_lufs':lufs,'final_tp':peak,'final_duration_s':qc.duration_s,
            'alignment_duration_s':aligned.duration_s,'resolution':f'{width}x{height}',
            'technical_qc':qc.model_dump(),'capture':capture.model_dump(),
            'actual_decisions':['SENT FOR MANAGER REVIEW · $120 · travel','AUTO-APPROVED · $80 · travel'],
            'source':'Original functional local application; entered example data',
            'live_llm_calls':0,'ready_for_publication':False,'publishing':'disabled'}
        (folder/'qc_report.json').write_text(json.dumps(report,indent=2))
        gates=enforce(folder,expected_size=(width,height))
        (folder/'independent_gates.json').write_text(json.dumps(gates,indent=2))
        for second,label in [(1,'hook'),(boundaries[2]+.5,'review'),(boundaries[4]+.5,'approved')]:
            subprocess.run(['ffmpeg','-y','-loglevel','error','-ss',str(second),'-i',str(folder/'final.mp4'),
                '-frames:v','1',str(folder/(label+'.jpg'))],check=True)
        reports[name]=report
    (out/'REPORT.json').write_text(json.dumps(reports,indent=2))
    return reports


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--voice',type=Path,required=True)
    p.add_argument('--output-dir',type=Path,default=Path('outputs/showcase'))
    p.add_argument('--format',choices=['both',*FORMATS],default='both')
    a=p.parse_args()
    print(json.dumps(run(a.voice,a.output_dir,list(FORMATS) if a.format=='both' else [a.format]),indent=2))
