"""Rendered technical checks, sampled motion evidence; semantic judgement stays explicit."""
import json,subprocess,re
from pathlib import Path

def rendered_qa(video,plan,out):
    import numpy as np
    from PIL import Image,ImageChops
    from .semantic_director import validate_film
    evidence=out/'visual-evidence';evidence.mkdir(exist_ok=True)
    shots=[];identity_checks=[];both_characters=None
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
        if shot['action'] in ('compose_send','receive'):
            full=evidence/(shot['shot_id']+'-identity.png')
            subprocess.run(['ffmpeg','-y','-v','error','-ss',str((shot['to']-12)/30),'-i',str(video),'-frames:v','1',str(full)],check=True)
            ocr=subprocess.check_output(['tesseract',str(full),'stdout','--psm','11'],stderr=subprocess.DEVNULL).decode()
            expected=re.sub('[^A-Z0-9]','',shot['application_id'].upper())
            identity_checks.append({'shot_id':shot['shot_id'],'expected_application':shot['application_id'],'visible_id_read_by_ocr':expected in re.sub('[^A-Z0-9]','',ocr.upper())})
        if shot['action']=='invite':
            both_characters=character_visibility(frames[-1],plan['director']['world'])
        sheet=Image.new('RGB',(810,480))
        for j,im in enumerate(frames):sheet.paste(im,(j*270,0))
        sheet.save(evidence/(shot['shot_id']+'-contact.jpg'))
        shots.append({'shot_id':shot['shot_id'],'action':shot['action'],'samples':samples,'mean_pixel_change':round(change,3),'not_black':luma>10,'has_visible_change':change>.18,'semantic_grounding':'manual review required'})
    structural=validate_film(plan)
    result={'passed':structural['passed'] and all(s['not_black'] and s['has_visible_change'] for s in shots) and all(v['visible_id_read_by_ocr'] for v in identity_checks) and bool(both_characters and both_characters['passed']),'structural':structural,'shots':shots,'visible_application_identity':identity_checks,'split_view_characters':both_characters,
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


def character_visibility(image,world):
    """Known original asset palette probe; not a general human detector."""
    import numpy as np
    image=image.resize((270,480)).convert('RGB');pixels=np.asarray(image,dtype=int)
    counts={}
    for key,x0,x1 in [('candidate',0,135),('recruiter',135,270)]:
        color=world[key]['shirt'].lstrip('#');rgb=np.array([int(color[i:i+2],16) for i in (0,2,4)])
        patch=pixels[80:330,x0:x1]
        counts[key]=int(np.sum(np.all(np.abs(patch-rgb)<16,axis=2)))
    return {'passed':all(v>=24 for v in counts.values()),'matching_shirt_pixels':counts,'scope':'Known procedural character assets, not general image recognition'}
