"""Native English Kokoro for the shared narrator interface; never clones a reference voice."""
import argparse,hashlib,json,tempfile,shutil
from pathlib import Path
from tiktok_motion.premium_job import narrate


def main():
    p=argparse.ArgumentParser();p.add_argument('--texts',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--voice',default='af_heart',choices=['af_heart','am_michael']);a=p.parse_args()
    texts=json.loads(a.texts.read_text())
    if not isinstance(texts,list) or not texts or any(not isinstance(t,str) or not t.strip() for t in texts):raise ValueError('Texts must be nonempty strings')
    a.out.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        work=Path(td)
        plan=narrate({'voice':a.voice,'scenes':[{'narration':t} for t in texts]},work)
        beats=[]
        for i,(text,s) in enumerate(zip(texts,plan['scenes'])):
            filename=f'seg_{i:03}.wav';shutil.copy2(work/f'speech_{i}.wav',a.out/filename)
            beats.append({'index':i,'file':filename,'sha1':hashlib.sha1(' '.join(text.split()).encode()).hexdigest(),'seconds':s['speech_seconds']})
        (a.out/'manifest.json').write_text(json.dumps({'engine':'kokoro','model':'Kokoro-82M','voice':a.voice,'language':'en','voice_owner_approved':False,'beats':beats}))
    print(json.dumps({'engine':'kokoro','language':'en','segments':len(beats)}))
if __name__=='__main__':main()
