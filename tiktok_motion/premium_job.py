"""Exact owner script -> measured English speech -> reusable Remotion premium scenes.

No publishing, paid API, cloned reference voice, or implicit renderer fallback.
"""
from __future__ import annotations
import argparse, hashlib, json, math, re, subprocess, wave
from pathlib import Path

from .story_scene import ALL_KINDS, enrich_visual

VOICES = {'af_heart', 'am_michael'}
ROOT = Path(__file__).resolve().parent
REMOTION = ROOT/'premium/remotion'


def validate_request(data):
    if not isinstance(data, dict): raise ValueError('Request must be an object')
    if data.get('language', 'en') != 'en': raise ValueError('This premium narrator currently supports English only')
    if data.get('voice', 'af_heart') not in VOICES: raise ValueError('Unsupported English voice')
    if data.get('profile', 'premium') not in ('premium', 'focus3d'): raise ValueError('Unsupported renderer')
    if data.get('visual_mode','premium') not in ('premium','cinematic'):raise ValueError('Unsupported visual mode')
    text = data.get('script')
    if data.get('profile') != 'focus3d':
        if not isinstance(text, str) or not 20 <= len(text) <= 12000 or len(text.split()) < 8:
            raise ValueError('Supply a complete script, not a topic prompt')
    return data


def make_plan(data, out):
    data=validate_request(data)
    text=data['script']
    director=None
    if data.get('geography') is not None:
        from .semantic_director import compile_geographic_script
        geographic = compile_geographic_script(text, data['geography'], data.get('geo_clip_id', 'director'), data.get('genre','documentary'))
        raw = geographic['scenes']; title = data['geography'].get('title', 'Geographic story')
    elif data.get('visual_mode')=='cinematic':
        from .semantic_director import compile_script
        director=compile_script(text,data.get('genre','education'))
        if not director['ready']:raise ValueError('Film needs assets/review: '+'; '.join(director['missing_requirements']))
        raw=director['scenes'];title='Applicant to recruiter · cinematic simulation'
    elif text.lstrip().startswith('{'):
        obj=json.loads(text)
        if obj.get('language','en') != 'en': raise ValueError('English script required')
        raw=obj.get('scenes',[]);title=obj.get('title','Owner script')
    else:
        raw=[{'narration':p.strip(), 'kind':'kinetic'} for p in re.split(r'\n\s*\n',text) if p.strip()]
        title='Your script · LogicScript'
    if not 1 <= len(raw) <= 20: raise ValueError('Use between one and twenty paragraphs/scenes')
    scenes=[]
    for i,s in enumerate(raw):
        n=s.get('narration');kind=s.get('kind','kinetic');items=s.get('items',[])
        if not isinstance(n,str) or not n.strip() or len(n)>3000: raise ValueError('Invalid scene narration')
        if kind not in ALL_KINDS: raise ValueError('Unsupported scene kind')
        if not isinstance(items,list) or len(items)>6 or any(not isinstance(v,str) or len(v)>60 for v in items): raise ValueError('Invalid labels')
        headline=s.get('on_screen') or ' '.join(n.split()[:7])
        if not isinstance(headline,str) or len(headline)>110: raise ValueError('Headline too long')
        # Fail closed if the vetted Cesium capture has not been installed.
        # A local God Eye clip is pre-rendered, never fetched during film rendering.
        if kind == 'god_eye':
            checked=enrich_visual(s)
            geo_file=REMOTION/'public'/checked['geo_clip']
            if not geo_file.is_file() or geo_file.stat().st_size<=0:
                raise ValueError('God Eye capture missing: prepare reviewed local MP4 first')
        scenes.append({'narration':n,'kind':kind,'headline':headline,'items':items,
                       'visual_notes':s.get('visual_notes',''), **enrich_visual(s)})
    plan={'title':str(title)[:150], 'scenes':scenes, 'language':'en','voice':data.get('voice','af_heart'),
          'source_sha256':hashlib.sha256(text.encode()).hexdigest(),'narration_rewritten':False,
          'requires_owner_approval':True,'auto_publish':False,'visual_notes_require_review':any(s['visual_notes'] for s in scenes)}
    if data.get('geography') is not None:plan['geographic_director']=geographic
    if director:plan['director']=director
    out.mkdir(parents=True,exist_ok=True)
    (out/'source.json').write_text(json.dumps(data,ensure_ascii=False))
    return plan


def captions_from_tokens(tokens, offset=0):
    """Use Kokoro's generated phoneme durations, never proportional word timings."""
    def text(words):
        value=re.sub(r'\s+([,.;:!?%])',r'\1',' '.join(words))
        return re.sub(r"(\w)\s*(['’])\s*(\w)",r'\1\2\3',value)
    captions=[];batch=[];start=None;end=None
    for token in tokens:
        a=getattr(token,'start_ts',None);b=getattr(token,'end_ts',None);word=getattr(token,'text','')
        if a is None or b is None or not word.strip(): continue
        if b<=a: continue
        if batch and (len(' '.join(batch+[word]))>38 or b-start>2.8):
            captions.append({'start':start+offset,'end':end+offset,'text':text(batch)})
            batch=[];start=None
        if start is None:start=float(a)
        end=float(b);batch.append(word)
    if batch:captions.append({'start':start+offset,'end':end+offset,'text':text(batch)})
    return captions


def validate_clip_duration(clip, required_seconds):
    """Reject short captures rather than freezing the last frame under narration."""
    info = json.loads(subprocess.check_output([
        'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
        '-of', 'json', str(clip)], text=True))
    duration = float(info.get('format', {}).get('duration') or 0)
    if not math.isfinite(duration) or duration + 1/60 < required_seconds:
        raise ValueError('Geographic capture is shorter than narrated scene; recapture to match speech')
    return duration


def narrate(plan, public_dir, pipeline=None):
    import numpy as np
    if pipeline is None:
        from kokoro import KPipeline
        pipeline=KPipeline(lang_code='a',repo_id='hexgrad/Kokoro-82M')
    total=0
    for i,s in enumerate(plan['scenes']):
        chunks=[];captions=[];word_times=[];offset=0
        for result in pipeline(s['narration'],voice=plan['voice'],speed=1.0):
            audio=np.asarray(result.audio,dtype=np.float32)
            if not len(audio) or not np.isfinite(audio).all():raise ValueError('Invalid generated speech')
            captions.extend(captions_from_tokens(result.tokens or [],offset))
            word_times.extend({'text':t.text,'start':float(t.start_ts)+offset,'end':float(t.end_ts)+offset} for t in (result.tokens or []) if t.start_ts is not None and t.end_ts is not None)
            chunks.append(audio);offset+=len(audio)/24000
        if not chunks or not captions:raise ValueError('Speech or native token timing missing')
        if offset>120:raise ValueError('Scene too long; divide the script into more paragraphs')
        raw=public_dir/f'raw_{i}.wav';dest=public_dir/f'speech_{i}.wav'
        import soundfile as sf
        sf.write(raw,np.concatenate(chunks),24000,subtype='PCM_16')
        subprocess.run(['ffmpeg','-y','-loglevel','error','-i',str(raw),'-af','loudnorm=I=-16:TP=-1.5:LRA=11','-ar','24000','-ac','1',str(dest)],check=True)
        with wave.open(str(dest)) as f: measured=f.getnframes()/f.getframerate()
        if abs(measured-offset)>.08:raise ValueError('Narration normalization changed timing')
        for c in captions:
            if c['start']<0 or c['end']>measured+.1:raise ValueError('Caption outside measured speech')
        s.update(audio=f'job/speech_{i}.wav',captions=captions,durationFrames=math.ceil((measured+(1.0 if plan.get('director') else .30))*30),speech_seconds=measured,words=word_times)
        if s['kind'] == 'god_eye':
            validate_clip_duration(REMOTION/'public'/s['geo_clip'], s['durationFrames']/30)
        total+=s['durationFrames']
    if total>600*30:raise ValueError('Maximum video duration is ten minutes')
    plan.update(durationInFrames=total,fps=30,width=1080,height=1920,
                renderer='remotion-semantic-film' if plan.get('director') else 'remotion-premium-owner-script',narration_backend='kokoro-en-native',
                caption_timing='kokoro_generated_token_durations',voice_owner_approved=False)
    if plan.get('director'):
        from .semantic_director import bind_timeline
        plan=bind_timeline(plan)
        from .film_qa import make_soundtrack
        make_soundtrack(plan,public_dir)
    return plan


def render(request, out, browser=None):
    out.mkdir(parents=True,exist_ok=True)
    public=REMOTION/'public/job';public.mkdir(parents=True,exist_ok=True)
    plan=narrate(make_plan(request,out),public)
    props=out/'props.json';props.write_text(json.dumps({'plan':plan},ensure_ascii=False))
    (out/'plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2))
    cmd=['npx','--no-install','remotion','render','src/index.ts','OwnerPremium',str((out/'final.mp4').resolve()),'--props',str(props.resolve()),'--concurrency=2','--crf=20','--pixel-format=yuv420p']
    if browser:cmd+=['--browser-executable',browser]
    subprocess.run(cmd,cwd=REMOTION,check=True)
    video=out/'final.mp4'
    from .media_qc import normalize_delivery
    normalize_delivery(video)
    info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(video)]))
    v=next(x for x in info['streams'] if x['codec_type']=='video');a=next(x for x in info['streams'] if x['codec_type']=='audio')
    duration=float(info['format']['duration'])
    if (v['width'],v['height'],v['codec_name'],a['codec_name'])!=(1080,1920,'h264','aac') or v.get('pix_fmt')!='yuv420p' or abs(duration-plan['durationInFrames']/30)>.15:raise ValueError('MP4 technical gate failed')
    subprocess.run(['ffmpeg','-v','error','-i',str(video),'-f','null','-'],check=True)
    report={k:plan[k] for k in ('source_sha256','renderer','narration_backend','caption_timing','voice','voice_owner_approved','narration_rewritten','requires_owner_approval','auto_publish')}
    report.update(duration_seconds=duration,scenes=len(plan['scenes']),technical_qc_passed=True,published=False,rendered=True,video_sha256=hashlib.sha256(video.read_bytes()).hexdigest())
    (out/'report.json').write_text(json.dumps(report,indent=2))
    if plan.get('director'):
        from .film_qa import rendered_qa
        report['visual_quality']=rendered_qa(video,plan,out)
        (out/'report.json').write_text(json.dumps(report,indent=2))
        if not report['visual_quality']['passed']:raise ValueError('Rendered film quality gate failed')
    # Speech-only audition from the same actual rendered voice.
    subprocess.run(['ffmpeg','-y','-loglevel','error','-i',str(video),'-t','15','-vn','-c:a','libmp3lame','-b:a','160k',str(out/'voice_sample.mp3')],check=True)
    return report


def main():
    p=argparse.ArgumentParser();p.add_argument('--request',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--browser')
    a=p.parse_args()
    report=render(json.loads(a.request.read_text()),a.out,a.browser)
    print(json.dumps(report))
if __name__=='__main__':main()

