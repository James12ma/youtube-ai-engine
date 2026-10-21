"""Fetch private owner script, execute the selected renderer, deliver only to owner."""
from __future__ import annotations
import argparse,hashlib,json,os,re,subprocess,sys
from pathlib import Path
import httpx
from tiktok_motion.premium_job import render,validate_request


def fetch_request(payload,token):
    if payload.get('profile')=='focus3d':return {'profile':'focus3d'}
    file_id=payload.get('file_id')
    if not isinstance(file_id,str) or not 1<=len(file_id)<=512:raise ValueError('Invalid source file')
    # Never raise a network exception containing the credential-bearing Telegram URL.
    try:
        with httpx.Client(timeout=60,follow_redirects=False) as client:
            r=client.post(f'https://api.telegram.org/bot{token}/getFile',json={'file_id':file_id})
            b=r.json()
            if r.status_code!=200 or b.get('ok') is not True:raise ValueError()
            path=b['result']['file_path']
            if not re.fullmatch(r'[a-zA-Z0-9_./-]+',path) or '..' in path:raise ValueError()
            r=client.get(f'https://api.telegram.org/file/bot{token}/{path}')
            if r.status_code!=200 or not 0<len(r.content)<=64000:raise ValueError()
            data=validate_request(r.json())
    except Exception:raise ValueError('Private source download failed') from None
    digest=hashlib.sha256(data['script'].encode()).hexdigest()
    if payload.get('source_sha256')!=digest:raise ValueError('Owner script hash mismatch')
    if data.get('profile','premium')!='premium' or data.get('voice','af_heart')!=payload.get('voice'):raise ValueError('Request profile mismatch')
    return data


def deliver(path,method,field,token,owner,caption):
    try:
        with path.open('rb') as f:
            r=httpx.post(f'https://api.telegram.org/bot{token}/{method}',data={'chat_id':owner,'caption':caption,'supports_streaming':'true'},files={field:(path.name,f)},timeout=180)
        ok=r.status_code==200 and r.json().get('ok') is True
    except Exception:raise ValueError('Private delivery failed') from None
    if not ok:raise ValueError('Telegram rejected private delivery')
    print(json.dumps({'delivery':method,'accepted':True}))


def run(payload,out,token,owner,browser=None):
    data=fetch_request(payload,token)
    out.mkdir(parents=True,exist_ok=True)
    if payload.get('mode')=='finance':
        from orchestrator.finance_runtime import finance_payload
        try:
            data=finance_payload(data)
        except Exception:
            # Preserve private delivery while keeping provider text/URLs and script out of logs.
            review=out/'review_needed.json'
            review.write_text(json.dumps({'reason':'Finance scene planning blocked or unavailable; check approved free-provider configuration and source integrity.',
                                          'requires_owner_review':True,'published':False},indent=2))
            (out/'report.json').write_text(json.dumps({'mode':'finance','status':'blocked',
                                                       'published':False,'requires_owner_review':True},indent=2))
            deliver(review,'sendDocument','document',token,owner,
                    'Plan finans bloke · pa gen videyo pibliye · verifikasyon nesesè')
            raise ValueError('Finance scene planning blocked') from None
    if data.get('profile')=='focus3d':
        base=Path('tiktok_motion/premium')
        env={**os.environ,'PREVIEW':'0','JOBS':'2'}
        if browser:env['CHROME']=browser
        subprocess.run(['bash',str(base/'render.sh')],env=env,check=True)
        import shutil
        shutil.copy2(base/'out/focus_prototype.mp4',out/'final.mp4')
        report={'renderer':'blender-cycles+remotion-focus','duration_seconds':13,'requires_owner_approval':True,'published':False,'voice':'none_original_score','technical_qc_passed':True}
        (out/'report.json').write_text(json.dumps(report,indent=2))
    else:
        try:report=render(data,out,browser)
        except ValueError as error:
            if data.get('visual_mode')!='cinematic':raise
            message=str(error)
            prefixes=('Film needs assets/review:','Film blocked:','Film editorial gate:','Rendered film quality gate failed','Native word alignment missing')
            reason=message if message.startswith(prefixes) else 'Film request needs asset or editorial review.'
            review=out/'review_needed.json'
            review.write_text(json.dumps({'reason':reason,'requires_owner_review':True,'published':False},indent=2))
            failure={'renderer':'remotion-semantic-film','status':'blocked','blocking_category':'asset_or_editorial_review','rendered':(out/'final.mp4').is_file(),'published':False,'auto_publish':False,'requires_owner_review':True,'private_review_delivered':False}
            (out/'report.json').write_text(json.dumps(failure,indent=2))
            deliver(review,'sendDocument','document',token,owner,'Film bloke pou revizyon · rezon yo nan dokiman prive sa a · pa pibliye')
            failure['private_review_delivered']=True
            (out/'report.json').write_text(json.dumps(failure,indent=2))
            raise ValueError('Film blocked; private owner review delivered') from None
    duration=report['duration_seconds'];maxrate=max(128,int(44_000_000*8/duration/1000-128))
    video=out/'telegram.mp4'
    subprocess.run(['ffmpeg','-y','-loglevel','error','-i',str(out/'final.mp4'),'-vf','scale=720:1280','-c:v','libx264','-preset','veryfast','-crf','22','-maxrate',f'{maxrate}k','-bufsize',f'{maxrate*2}k','-c:a','aac','-b:a','128k','-movflags','+faststart',str(video)],check=True)
    if video.stat().st_size>=49_000_000:raise ValueError('Telegram output exceeds delivery limit')
    # Delivery is a required gate, not a green job hiding a failed send.
    deliver(video,'sendVideo','video',token,owner,'LogicScript · Premium preview · pou revizyon ou · pa pibliye')
    if (out/'voice_sample.mp3').is_file():deliver(out/'voice_sample.mp3','sendAudio','audio',token,owner,'Nouvo vwa anglè Kokoro · echantiyon 15 s · poko apwouve pa ou')
    report.update(telegram_accepted=True)
    (out/'report.json').write_text(json.dumps(report,indent=2))
    return report


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=Path('outputs/premium'));p.add_argument('--browser')
    a=p.parse_args()
    try:
        payload=json.loads(os.environ['PREMIUM_PAYLOAD'])
        report=run(payload,a.out,os.environ['TG'],os.environ['OWNER'],a.browser)
        print(json.dumps(report))
    except Exception as e:
        # Do not echo source text, raw provider errors, or credential-bearing URLs.
        print('::error::Premium job failed: '+type(e).__name__)
        return 1
    return 0
if __name__=='__main__':sys.exit(main())
