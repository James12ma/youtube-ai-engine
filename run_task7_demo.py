from __future__ import annotations
import argparse,json
from pathlib import Path
from production_pro.demo import run_demo
p=argparse.ArgumentParser()
p.add_argument('--engineering-voice',action='store_true')
p.add_argument('--piper-model',type=Path)
p.add_argument('--size',choices=['1280x720','1920x1080'],default='1280x720')
p.add_argument('--output',type=Path,default=Path('task7_demo.mp4'))
a=p.parse_args()
if not a.engineering_voice and a.piper_model is None:p.error('Specify --piper-model path, or --engineering-voice for noncommercial quality test')
w,h=map(int,a.size.split('x'))
r=run_demo(Path('task7_demo_work'),a.output,piper_model=a.piper_model,engineering_voice=a.engineering_voice,size=(w,h))
print(json.dumps(r,indent=2))
