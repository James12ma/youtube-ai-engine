"""Canonical H264/yuv420p TV-range delivery, preserving AAC audio bitstream."""
import argparse,json,subprocess,os
from pathlib import Path

def normalize_delivery(path):
    path=Path(path)
    info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-of','json',str(path)]))
    video=next(s for s in info['streams'] if s['codec_type']=='video')
    if video['codec_name']=='h264' and video.get('pix_fmt')=='yuv420p' and video.get('color_range')!='pc':return
    temp=path.with_name(path.stem+'.normalized.mp4')
    subprocess.run(['ffmpeg','-y','-v','error','-i',str(path),'-map','0:v:0','-map','0:a:0?',
                    '-vf','scale=in_range=auto:out_range=tv,format=yuv420p','-c:v','libx264','-preset','fast','-crf','18',
                    '-color_range','tv','-c:a','copy','-movflags','+faststart',str(temp)],check=True)
    fixed=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-of','json',str(temp)]))
    v=next(s for s in fixed['streams'] if s['codec_type']=='video')
    if (v['codec_name'],v.get('pix_fmt'))!=('h264','yuv420p'):raise ValueError('Canonical delivery format failed')
    os.replace(temp,path)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('video',type=Path);normalize_delivery(p.parse_args().video)
