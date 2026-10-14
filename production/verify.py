from __future__ import annotations
import json,subprocess
from pathlib import Path
from .audio import loudness
from .errors import VerifyError
from .models import RenderReport,RenderConfig

def probe(path:Path):
    p=subprocess.run(['ffprobe','-v','error','-print_format','json','-show_format','-show_streams',str(path)],capture_output=True,text=True)
    if p.returncode: raise VerifyError('ffprobe failed')
    return json.loads(p.stdout)

def verify(path:Path,config:RenderConfig,*,audio_duration:float,caption_count:int,caption_file:str,scene_count:int,tts_backend:str):
    if not path.exists() or path.stat().st_size<1024: raise VerifyError('output missing or too small')
    data=probe(path)
    v=next((s for s in data['streams'] if s['codec_type']=='video'),None)
    a=next((s for s in data['streams'] if s['codec_type']=='audio'),None)
    if not v or not a: raise VerifyError('missing audio/video stream')
    if (v.get('width'),v.get('height'))!=(config.width,config.height): raise VerifyError('wrong resolution')
    if config.require_captions and (not caption_count or not caption_file): raise VerifyError('required captions missing')
    duration=float(data['format']['duration'])
    if abs(duration-audio_duration)>.35: raise VerifyError(f'audio/video duration drift {duration:.2f} vs {audio_duration:.2f}')
    l=loudness(path,config.audio_lufs,config.audio_tp,config.audio_lra)
    lufs=float(l['input_i']);peak=float(l['input_tp'])
    if abs(lufs-config.audio_lufs)>2.0 or peak>config.audio_tp+.6: raise VerifyError(f'audio loudness fails: {lufs}, TP {peak}')
    n,d=v['r_frame_rate'].split('/');fps=float(n)/float(d)
    warnings=['No publication, revenue, or monetization readiness implied']
    if tts_backend=='fake': warnings.append('SYNTHETIC TEST TONE — NOT SPOKEN NARRATION')
    if tts_backend=='espeak-estimated': warnings.append('eSpeak narration is robotic and caption word timings are only approximations')
    return RenderReport(output_path=str(path.resolve()),duration_s=duration,width=v['width'],height=v['height'],fps=fps,video_codec=v['codec_name'],audio_codec=a['codec_name'],audio_lufs=lufs,audio_true_peak=peak,file_size_bytes=path.stat().st_size,scene_count=scene_count,caption_count=caption_count,caption_file=caption_file,tts_backend=tts_backend,ready_for_publication=False,warnings=warnings)
