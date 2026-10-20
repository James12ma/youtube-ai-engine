"""Rendered technical checks, sampled motion evidence; semantic judgement stays explicit."""
import json,subprocess
from pathlib import Path

def rendered_qa(video,plan,out):
    import numpy as np
    from PIL import Image,ImageChops
    from .semantic_director import validate_film
    evidence=out/'visual-evidence';evidence.mkdir(exist_ok=True)
    shots=[]
    for shot in plan['director']['shots']:
        frames=[];samples=[]
        # Start, exact native-word action, late consequence: not just pretty title frames.
        points=[min(shot['to']-1,shot['from']+3),shot['action_frame'],max(shot['from'],shot['to']-6)]
        for j,f in enumerate(points):
            path=evidence/f"{shot['shot_id']}-{j}.png"
            subprocess.run(['ffmpeg','-y','-v','error','-ss',str(f/30),'-i',str(video),'-frames:v','1','-vf','scale=270:480',str(path)],check=True)
            im=Image.open(path).convert('RGB');frames.append(im.copy());samples.append({'frame':f,'file':path.name})
        a=np.asarray(frames[0].crop((0,45,270,390)),dtype=float);b=np.asarray(frames[-1].crop((0,45,270,390)),dtype=float)
        change=float(np.mean(np.abs(a-b)));luma=float(np.mean(b))
        sheet=Image.new('RGB',(810,480))
        for j,im in enumerate(frames):sheet.paste(im,(j*270,0))
        sheet.save(evidence/(shot['shot_id']+'-contact.jpg'))
        shots.append({'shot_id':shot['shot_id'],'action':shot['action'],'samples':samples,'mean_pixel_change':round(change,3),'not_black':luma>10,'has_visible_change':change>.18,'semantic_grounding':'manual review required'})
    structural=validate_film(plan)
    result={'passed':structural['passed'] and all(s['not_black'] and s['has_visible_change'] for s in shots),'structural':structural,'shots':shots,
            'limitations':'Pixel change detects static/black execution, not semantic correctness, OCR, human anatomy or factual truth. Independent visual review required.'}
    (out/'visual-qa.json').write_text(json.dumps(result,indent=2))
    return result


def make_soundtrack(plan,public):
    import numpy as np,wave
    sr=24000;audio=np.zeros(round(plan['durationInFrames']/30*sr),dtype=np.float32)
    for shot in plan['director']['shots']:
        if shot['action'] not in ('compose_send','receive','invite'):continue
        t=np.arange(int(sr*.22))/sr
        hz={'compose_send':800,'receive':1100,'invite':650}[shot['action']]
        cue=.022*np.sin(2*np.pi*hz*t)*np.exp(-t*25)
        start=int(shot['action_frame']/30*sr);end=min(len(audio),start+len(cue));audio[start:end]+=cue[:end-start]
    path=public/'film_fx.wav'
    with wave.open(str(path),'wb') as f:f.setparams((1,2,sr,0,'NONE','not compressed'));f.writeframes((np.clip(audio,-1,1)*32767).astype('<i2').tobytes())
    plan['director']['soundtrack']='job/film_fx.wav'
