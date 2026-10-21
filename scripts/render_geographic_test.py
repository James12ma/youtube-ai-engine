"""Exact narration -> word cues -> upstream capture -> existing Remotion composition.

All assets are local, public-domain Natural Earth / original artwork. No API keys,
external feeds, publishing or deployment. Run from the repository root.
"""
import argparse
import hashlib
import json
import math
import shutil
import subprocess
from pathlib import Path
from tiktok_motion.geographic_director import validate_geography, compile_geographic_scene
from tiktok_motion.premium_job import narrate, validate_clip_duration

ROOT = Path(__file__).resolve().parents[1]
REMOTION = ROOT/'tiktok_motion/premium/remotion'


def render(upstream, spec_file, out, browser=None, voice_plan=None, capture_dir=None):
    spec=validate_geography(json.loads(spec_file.read_text()))
    out=out.resolve();out.mkdir(parents=True,exist_ok=True)
    voice_dir=out/'voice';voice_dir.mkdir(exist_ok=True)
    if voice_plan:
        plan=json.loads(voice_plan.read_text())
        if plan['scenes'][0]['narration'] != spec['narration']:
            raise ValueError('Cached voice does not match exact narration')
        shutil.copyfile(voice_plan.parent/'speech_0.wav',voice_dir/'speech_0.wav')
    else:
        plan=narrate({'voice':'af_heart','scenes':[{'kind':'kinetic','narration':spec['narration']}]},voice_dir)
    words=plan['scenes'][0]['words']
    # Each cue is an exact sentence. Bind its first word to native audio timing.
    from tiktok_motion.semantic_director import _trigger_time
    for cue in spec['cues']:
        cue['at']=_trigger_time(words,cue['phrase'])
    spec['cues'][0]['at']=0
    spec['duration']=max(10,spec['duration'],math.ceil((plan['scenes'][0]['speech_seconds']+1.5)*30)/30)
    if spec['duration']>15:
        raise ValueError('Test narration exceeds 15 second acceptance limit')
    validate_geography(spec)
    storyboard=out/'storyboard.json';storyboard.write_text(json.dumps(spec,indent=2))
    (voice_dir/'voice_plan.json').write_text(json.dumps(plan,indent=2))
    capture=capture_dir.resolve() if capture_dir else out/'capture'
    # A fully rendered, matching capture is reusable without opening WebGL again.
    # Its source hash must match both the browser renderer and capture driver.
    renderer_hash=hashlib.sha256((ROOT/'scripts/geo_capture/browser.mjs').read_bytes()+(ROOT/'scripts/capture_god_eye.mjs').read_bytes()).hexdigest()
    cached=False
    if (capture/'capture.json').is_file() and (capture/'capture.mp4').is_file():
        metadata=json.loads((capture/'capture.json').read_text())
        if metadata.get('spec')==spec and metadata.get('rendererHash')==renderer_hash:
            probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0','-show_entries','stream=nb_frames,width,height,codec_name','-of','json',str(capture/'capture.mp4')]))['streams'][0]
            cached=(int(probe.get('nb_frames',0))==round(spec['duration']*30) and (probe['width'],probe['height'],probe['codec_name'])==(1280,720,'h264'))
    if not cached:
        subprocess.run(['node',str(ROOT/'scripts/capture_god_eye.mjs'),str(upstream.resolve()),str(storyboard),str(capture)],cwd=ROOT,check=True)
    else:
        print('Reusing complete source-bound geographic capture',flush=True)
    validate_clip_duration(capture/'capture.mp4',spec['duration'])
    public=REMOTION/'public/job';public.mkdir(exist_ok=True)
    shutil.copyfile(capture/'capture.mp4',public/'god_eye_director.mp4')
    shutil.copyfile(voice_dir/'speech_0.wav',public/'geo_speech.wav')
    from tiktok_motion.semantic_director import compile_geographic_script
    director=compile_geographic_script(spec['narration'],spec)
    scene=director['scenes'][0]
    props={'plan':{'geo_clip':scene['geo_clip'],'geo_attribution':scene['geo_attribution'],'audio':'job/geo_speech.wav','durationInFrames':round(spec['duration']*30)}}
    props_file=out/'props.json';props_file.write_text(json.dumps(props,indent=2))
    cmd=['npx','--no-install','remotion','render','src/index.ts','GeoCinematic',str(out/'Gods_Eye_Atlantic_Test.mp4'),'--props',str(props_file),'--concurrency=1','--crf=18','--gl=swangle']
    if browser:cmd+=['--browser-executable',str(browser)]
    subprocess.run(cmd,cwd=REMOTION,check=True)
    video=out/'Gods_Eye_Atlantic_Test.mp4'
    subprocess.run(['ffmpeg','-v','error','-i',str(video),'-f','null','-'],check=True)
    info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(video)]))
    v=next(x for x in info['streams'] if x['codec_type']=='video');a=next(x for x in info['streams'] if x['codec_type']=='audio')
    if (v['width'],v['height'],v['codec_name'],a['codec_name'])!=(1280,720,'h264','aac') or abs(float(info['format']['duration'])-spec['duration'])>.1:
        raise ValueError('Geographic MP4 technical gate failed')
    frames=out/'review';frames.mkdir(exist_ok=True)
    for second in (1,4,7,10):
        subprocess.run(['ffmpeg','-y','-loglevel','error','-ss',str(second),'-i',str(video),'-frames:v','1',str(frames/f'frame_{second:02d}s.png')],check=True)
    report={'rendered':True,'technical_qc_passed':True,'duration_seconds':float(info['format']['duration']),'width':v['width'],'height':v['height'],'fps':v['r_frame_rate'],'video_sha256':hashlib.sha256(video.read_bytes()).hexdigest(),'scene':scene,'director':director,'capture':json.loads((capture/'capture.json').read_text()),'timing_source':'Kokoro native word timestamps','narration_rewritten':False,'terrain':'WGS84 ellipsoid, no elevation data','human_visual_review_required':True,'published':False,'deployed':False,'auto_publish':False}
    (out/'report.json').write_text(json.dumps(report,indent=2))
    return report


def main():
    p=argparse.ArgumentParser();p.add_argument('--upstream',required=True,type=Path);p.add_argument('--spec',type=Path,default=ROOT/'examples/god_eye_atlantic.json');p.add_argument('--out',required=True,type=Path);p.add_argument('--browser',type=Path);p.add_argument('--voice-plan',type=Path);p.add_argument('--capture-dir',type=Path)
    a=p.parse_args();print(json.dumps(render(a.upstream,a.spec,a.out,a.browser,a.voice_plan,a.capture_dir),indent=2))

if __name__=='__main__':main()
