"""Exact owner script -> measured English speech -> reusable Remotion premium scenes.

No publishing, paid API, cloned reference voice, or implicit renderer fallback.
"""
from __future__ import annotations
import argparse, hashlib, json, math, re, subprocess, wave
from pathlib import Path

VOICES = {'af_heart', 'am_michael'}
ROOT = Path(__file__).resolve().parent
REMOTION = ROOT/'premium/remotion'


def validate_request(data):
    if not isinstance(data, dict): raise ValueError('Request must be an object')
    if data.get('language', 'en') != 'en': raise ValueError('This premium narrator currently supports English only')
    if data.get('voice', 'af_heart') not in VOICES: raise ValueError('Unsupported English voice')
    if data.get('profile', 'premium') not in ('premium', 'focus3d'): raise ValueError('Unsupported renderer')
    text = data.get('script')
    if data.get('profile') != 'focus3d':
        if not isinstance(text, str) or not 20 <= len(text) <= 12000 or len(text.split()) < 8:
            raise ValueError('Supply a complete script, not a topic prompt')
    return data


def make_plan(data, out):
    data=validate_request(data)
    text=data['script']
    if text.lstrip().startswith('{'):
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
        if kind not in ('kinetic','cards','process','ui','timeline','chart'): raise ValueError('Unsupported scene kind')
        if not isinstance(items,list) or len(items)>6 or any(not isinstance(v,str) or len(v)>60 for v in items): raise ValueError('Invalid labels')
        headline=s.get('on_screen') or ' '.join(n.split()[:7])
        if not isinstance(headline,str) or len(headline)>110: raise ValueError('Headline too long')
        scenes.append({'narration':n,'kind':kind,'headline':headline,'items':items,
                       'visual_notes':s.get('visual_notes','')})
    plan={'title':str(title)[:150], 'scenes':scenes, 'language':'en','voice':data.get('voice','af_heart'),
          'source_sha256':hashlib.sha256(text.encode()).hexdigest(),'narration_rewritten':False,
          'requires_owner_approval':True,'auto_publish':False,'visual_notes_require_review':any(s['visual_notes'] for s in scenes)}
    out.mkdir(parents=True,exist_ok=True)
    (out/'source.json').write_text(json.dumps(data,ensure_ascii=False))
    return plan


def captions_from_tokens(tokens, offset=0):
    """Use Kokoro's generated phoneme durations, never proportional word timings."""
    captions=[];batch=[];start=None;end=None
    for token in tokens:
        a=getattr(token,'start_ts',None);b=getattr(token,'end_ts',None);word=getattr(token,'text','')
        if a is None or b is None or not word.strip(): continue
        if b<=a: continue
        if batch and (len(' '.join(batch+[word]))>38 or b-start>2.8):
            captions.append({'start':start+offset,'end':end+offset,'text':' '.join(batch)})
            batch=[];start=None
        if start is None:start=float(a)
        end=float(b);batch.append(word)
    if batch:captions.append({'start':start+offset,'end':end+offset,'text':' '.join(batch)})
    return captions


def narrate(plan, public_dir, pipeline=None):
    import numpy as np
    if pipeline is None:
        from kokoro import KPipeline
        pipeline=KPipeline(lang_code='a',repo_id='hexgrad/Kokoro-82M')
    total=0
    for i,s in enumerate(plan['scenes']):
        chunks=[];captions=[];offset=0
        for result in pipeline(s['narration'],voice=plan['voice'],speed=1.0):
            audio=np.asarray(result.audio,dtype=np.float32)
            if not len(audio) or not np.isfinite(audio).all():raise ValueError('Invalid generated speech')
            captions.extend(captions_from_tokens(result.tokens or [],offset))
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
        s.update(audio=f'job/speech_{i}.wav',captions=captions,durationFrames=math.ceil((measured+.30)*30),speech_seconds=measured)
        total+=s['durationFrames']
    if total>600*30:raise ValueError('Maximum video duration is ten minutes')
    plan.update(durationInFrames=total,fps=30,width=1080,height=1920,
                renderer='remotion-premium-owner-script',narration_backend='kokoro-en-native',
                caption_timing='kokoro_generated_token_durations',voice_owner_approved=False)
    return plan


def render(request, out, browser=None):
    out.mkdir(parents=True,exist_ok=True)
    public=REMOTION/'public/job';public.mkdir(parents=True,exist_ok=True)
    plan=narrate(make_plan(request,out),public)
    props=out/'props.json';props.write_text(json.dumps({'plan':plan},ensure_ascii=False))
    (out/'plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2))
    cmd=['npx','--no-install','remotion','render','src/index.ts','OwnerPremium',str((out/'final.mp4').resolve()),'--props',str(props.resolve()),'--concurrency=2','--crf=20']
    if browser:cmd+=['--browser-executable',browser]
    subprocess.run(cmd,cwd=REMOTION,check=True)
    video=out/'final.mp4'
    info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(video)]))
    v=next(x for x in info['streams'] if x['codec_type']=='video');a=next(x for x in info['streams'] if x['codec_type']=='audio')
    duration=float(info['format']['duration'])
    if (v['width'],v['height'],v['codec_name'],a['codec_name'])!=(1080,1920,'h264','aac') or abs(duration-plan['durationInFrames']/30)>.15:raise ValueError('MP4 technical gate failed')
    subprocess.run(['ffmpeg','-v','error','-i',str(video),'-f','null','-'],check=True)
    report={k:plan[k] for k in ('source_sha256','renderer','narration_backend','caption_timing','voice','voice_owner_approved','narration_rewritten','requires_owner_approval','auto_publish')}
    report.update(duration_seconds=duration,scenes=len(plan['scenes']),technical_qc_passed=True,published=False,rendered=True,video_sha256=hashlib.sha256(video.read_bytes()).hexdigest())
    (out/'report.json').write_text(json.dumps(report,indent=2))
    # Speech-only audition from the same actual rendered voice.
    subprocess.run(['ffmpeg','-y','-loglevel','error','-i',str(video),'-t','15','-vn','-c:a','libmp3lame','-b:a','160k',str(out/'voice_sample.mp3')],check=True)
    return report


def main():
    p=argparse.ArgumentParser();p.add_argument('--request',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--browser')
    a=p.parse_args()
    report=render(json.loads(a.request.read_text()),a.out,a.browser)
    print(json.dumps(report))
if __name__=='__main__':main()
