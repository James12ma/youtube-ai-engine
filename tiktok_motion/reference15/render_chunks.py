"""Resume-safe chunk renderer for the 98s career explainer, zero-cost and offline.

python -m tiktok_motion.reference15.render_chunks --output outputs/career98.mp4
python -m tiktok_motion.reference15.render_chunks --output outputs/career98.mp4 --only-chunk 2

Produces stable scene-aligned short H.264 chunks, one full offline soundtrack, and
an owner-approval-required report. Do not use for unattended publication.
"""
from __future__ import annotations
import argparse
import json
import subprocess
import tempfile
from pathlib import Path
from .longform import DURATION, FPS, SEGMENTS, frame, generate_audio


def render_one(cache:Path,index:int,start:int,end:int):
    output=cache/f'part_{index:02}.mp4'
    if output.exists() and output.stat().st_size>2000:
        p=subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nk=1:nw=1',str(output)],capture_output=True,text=True)
        try: existing_duration=float(p.stdout.strip())
        except ValueError: existing_duration=-1
        if abs(existing_duration-(end-start))<.1:
            return {'index':index,'status':'reused','path':str(output)}
    cmd=['ffmpeg','-hide_banner','-nostdin','-loglevel','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s','720x1280','-r',str(FPS),'-i','pipe:0','-vf','scale=1080:1920:flags=lanczos,format=yuv420p','-c:v','libx264','-preset','veryfast','-crf','22','-r',str(FPS),'-an','-movflags','+faststart',str(output)]
    process=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
    try:
        for f in range(start*FPS,end*FPS):process.stdin.write(frame(f/FPS).tobytes())
        process.stdin.close();err=process.stderr.read();r=process.wait()
    except BaseException:
        process.kill();process.wait();raise
    if r:raise RuntimeError(err.decode(errors='replace'))
    return {'index':index,'status':'rendered','path':str(output)}


def run(output:Path,only_chunk:int|None=None):
    output=output.resolve();output.parent.mkdir(exist_ok=True,parents=True)
    cache=output.parent/(output.stem+'_parts');cache.mkdir(exist_ok=True)
    edges=[0,16,32,48,64,80,DURATION]
    if only_chunk is not None:
        if not 0<=only_chunk<len(edges)-1:raise ValueError('only_chunk must be 0..5')
        return render_one(cache,only_chunk,edges[only_chunk],edges[only_chunk+1])
    statuses=[render_one(cache,i,a,b) for i,(a,b) in enumerate(zip(edges,edges[1:]))]
    audio=cache/'original_voice_and_score.wav'
    if not audio.exists():generate_audio(audio,with_voice=True,seconds=DURATION)
    lst=cache/'chunks.txt'
    lst.write_text(''.join(f"file '{(cache/f'part_{i:02}.mp4').as_posix()}'\n" for i in range(len(edges)-1)))
    subprocess.run(['ffmpeg','-hide_banner','-nostdin','-loglevel','error','-y','-f','concat','-safe','0','-i',str(lst),'-i',str(audio),'-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','128k','-t',str(DURATION),'-movflags','+faststart',str(output)],check=True)
    probe=json.loads(subprocess.run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(output)],capture_output=True,text=True,check=True).stdout)
    v=next(s for s in probe['streams'] if s['codec_type']=='video')
    duration=float(probe['format']['duration']);audio_ok=any(s['codec_type']=='audio' for s in probe['streams'])
    passed=abs(duration-DURATION)<.25 and v['width']==1080 and v['height']==1920 and audio_ok
    report={'duration':duration,'fps':FPS,'output':str(output),'chunks':statuses,'technical_check':'passed' if passed else 'failed','quality_note':'Robotic eSpeak voice; freeze holds >2s detected in local pilot. Owner premium gate pending.', 'requires_owner_approval':True,'auto_publish':False,'paid_services_used':False}
    output.with_suffix('.engine_run.json').write_text(json.dumps(report,indent=2))
    if not passed:raise RuntimeError('Technical QA failed')
    return report

if __name__=='__main__':
    cli=argparse.ArgumentParser();cli.add_argument('--output',type=Path,required=True);cli.add_argument('--only-chunk',type=int)
    args=cli.parse_args();print(json.dumps(run(args.output,args.only_chunk),indent=2))