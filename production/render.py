from __future__ import annotations
import subprocess,tempfile,shutil
from pathlib import Path
from pipeline.models import ScriptArtifact,StoryboardOutput
from .models import RenderConfig,RenderReport
from .tts import TTSBackend,probe_duration
from .audio import concat_wavs,normalize
from .assets import card
from .motion import make_clip
from .captions import group_words,write_ass
from .errors import RenderError,FFmpegMissingError,UnsafeVisualError
from .verify import verify

def _concat_video(clips:list[Path],dest:Path):
    listfile=dest.parent/'video_inputs.txt'
    if any("'" in str(p) or '\n' in str(p) for p in clips): raise RenderError('unsafe file path')
    listfile.write_text(''.join(f"file '{p.resolve()}'\n" for p in clips))
    p=subprocess.run(['ffmpeg','-y','-hide_banner','-loglevel','error','-f','concat','-safe','0','-i',str(listfile),'-c','copy',str(dest)],capture_output=True,text=True)
    if p.returncode: raise RenderError('concat video failed: '+p.stderr[-600:])

def render_video(script:ScriptArtifact,storyboard:StoryboardOutput,output_path:Path,tts:TTSBackend,*,config:RenderConfig|None=None,workdir:Path|None=None,approved:bool=False)->RenderReport:
    cfg=config or RenderConfig()
    if not approved: raise RenderError('script/storyboard must be explicitly review-approved before rendering')
    if not shutil.which('ffmpeg') or not shutil.which('ffprobe'): raise FFmpegMissingError('ffmpeg/ffprobe missing')
    if not script.hook.strip() or not script.cta.strip(): raise RenderError('hook and CTA are required')
    if not script.sections: raise RenderError('no script sections')
    if not storyboard.scenes: raise RenderError('missing storyboard')
    if any(s.visual_type in ('chart','screen_recording') for s in storyboard.scenes):
        raise UnsafeVisualError('real chart data and real screen-recording assets required before rendering; no fake placeholders')
    # prohibit missing sections, extra/unordered/overlapping scenes in this small prototype
    if set(s.section_index for s in storyboard.scenes)!=set(range(len(script.sections))):
        raise RenderError('storyboard must cover every script section')
    for i,s in enumerate(storyboard.scenes):
        if s.end_s<=s.start_s or s.section_index<0 or s.section_index>=len(script.sections): raise RenderError('invalid scene')
        if i and s.start_s<storyboard.scenes[i-1].end_s-.01: raise RenderError('scene overlaps')
    wd=workdir or Path(tempfile.mkdtemp(prefix='yt-render-'));wd.mkdir(parents=True,exist_ok=True)
    output_path.parent.mkdir(parents=True,exist_ok=True)
    parts=[('HOOK',script.hook,'text_overlay','Opening hook')]
    for idx,sec in enumerate(script.sections):
        scenes=[s for s in storyboard.scenes if s.section_index==idx]
        if not sec.narration.strip(): raise RenderError('empty section narration')
        # MVP: one section represented by one scene, no falsified demos.
        scene=scenes[0]
        if len(scenes)!=1: raise RenderError('MVP requires exactly one verified scene per section')
        parts.append((sec.heading,sec.narration,scene.visual_type,sec.on_screen_text or scene.instruction))
    parts.append(('NEXT STEP',script.cta,'text_overlay','Call to action'))
    audio_paths=[];clips=[];blocks=[];offset=0.;backend_names=set()
    for idx,(title,text,kind,screen_text) in enumerate(parts):
        output_wav=wd/f'audio_{idx}.wav'
        synthesized=tts.synthesize(text,output_wav)
        backend_names.add(synthesized.backend)
        converted=wd/f'pcm_{idx}.wav'
        p=subprocess.run(['ffmpeg','-y','-hide_banner','-loglevel','error','-i',str(output_wav),'-ar','48000','-ac','1','-c:a','pcm_s16le',str(converted)],capture_output=True,text=True)
        if p.returncode: raise RenderError('wav conversion failed: '+p.stderr[-300:])
        duration=probe_duration(converted)
        if duration<.5: raise RenderError('narration too short')
        audio_paths.append(converted)
        relative=group_words(synthesized.word_timings,cfg.caption_max_chars)
        for block in relative:
            blocks.append({'start_s':offset+block['start_s'],'end_s':min(offset+duration,offset+block['end_s']),'text':block['text']})
        img=wd/f'slide_{idx}.png';clip=wd/f'clip_{idx}.mp4'
        card(kind,title,screen_text,(cfg.width,cfg.height),img)
        make_clip(img,clip,duration,cfg.width,cfg.height,cfg.fps,cfg.crf,cfg.preset,cfg.temp_scale)
        clips.append(clip);offset+=duration
    if cfg.require_captions and not blocks: raise RenderError('no word timings for captions')
    combined=wd/'combined.wav';concat_wavs(audio_paths,combined)
    normalized=wd/'normalized.wav';normalize(combined,normalized,cfg.audio_lufs,cfg.audio_tp,cfg.audio_lra)
    audio_duration=probe_duration(normalized)
    silent=wd/'silent.mp4';_concat_video(clips,silent)
    ass=wd/'captions.ass';count=write_ass(blocks,ass,cfg.width,cfg.height,cfg.caption_font,cfg.caption_size)
    if not shutil.which('ffmpeg'): raise RenderError('ffmpeg missing')
    filter_arg='ass='+str(ass).replace(':','\\:').replace("'","\\'")
    cmd=['ffmpeg','-y','-hide_banner','-loglevel','error','-i',str(silent),'-i',str(normalized),'-vf',filter_arg,'-c:v','libx264','-threads','2','-preset',cfg.preset,'-crf',str(cfg.crf),'-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-movflags','+faststart','-shortest',str(output_path)]
    p=subprocess.run(cmd,capture_output=True,text=True,timeout=180)
    if p.returncode: raise RenderError('mux failed: '+p.stderr[-700:])
    return verify(output_path,cfg,audio_duration=audio_duration,caption_count=count,caption_file=str(ass),scene_count=len(parts),tts_backend=next(iter(backend_names)) if len(backend_names)==1 else 'mixed')
