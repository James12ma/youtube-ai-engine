"""Fail-closed media stream and subtitle coverage checks; no invented VMAF scores."""
from __future__ import annotations
import json,re,subprocess
from pathlib import Path
from .models import QCReport
from .errors import QCFailure
from production.audio import loudness

def _run_ffmpeg(path:Path,filter_spec:str, video=True):
 p=subprocess.run(['ffmpeg','-hide_banner','-nostats','-i',str(path),'-vf' if video else '-af',filter_spec,'-f','null','-'],capture_output=True,text=True)
 if p.returncode:raise QCFailure(['ffmpeg QC failed'],{'stderr':p.stderr[-300:]})
 return p.stderr

def _probe(path:Path)->dict:
 p=subprocess.run(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(path)],capture_output=True,text=True,check=True)
 return json.loads(p.stdout)

def _black_ratio(path:Path,duration:float)->float:
 log=_run_ffmpeg(path,'blackdetect=d=0.12:pix_th=0.11',True)
 intervals=re.findall(r'black_start:\s*([\d.]+)\s+black_end:\s*([\d.]+)\s+black_duration:',log)
 return min(1.,sum(max(0.,float(b)-float(a)) for a,b in intervals)/duration) if duration else 0.

def _silence_ratio(path:Path,duration:float)->float:
 log=_run_ffmpeg(path,'silencedetect=noise=-48dB:d=0.3',False)
 starts=[float(s) for s in re.findall(r'silence_start:\s*([\d.]+)',log)]
 ends=[float(e) for e in re.findall(r'silence_end:\s*([\d.]+)',log)]
 if len(starts)>len(ends):ends.append(duration)
 return min(1.,sum(max(0.,b-a) for a,b in zip(starts,ends))/duration) if duration else 0.

def _ass_caption_coverage(path:Path,duration:float)->float:
 def sec(s):
  h,m,v=s.split(':');return int(h)*3600+int(m)*60+float(v)
 spans=[]
 for line in path.read_text(encoding='utf-8').splitlines():
  if line.startswith('Dialogue:'):
   fields=line.split(',',3)
   if len(fields)>=3:spans.append((max(0.,sec(fields[1])),min(duration,sec(fields[2]))))
 spans.sort();merged=[]
 for a,b in spans:
  if b<=a:continue
  if merged and a<=merged[-1][1]:merged[-1]=(merged[-1][0],max(merged[-1][1],b))
  else:merged.append((a,b))
 return min(1.,sum(b-a for a,b in merged)/duration) if duration else 0.

def run_qc(video_path:Path,captions_ass:Path,*,min_caption_coverage=0.82,lufs_target=-16.0,allow_approximate=False,forced_alignment_verified=False)->QCReport:
 p=_probe(video_path)
 video=next((s for s in p['streams'] if s['codec_type']=='video'),None)
 audio=next((s for s in p['streams'] if s['codec_type']=='audio'),None)
 if video is None or audio is None:raise QCFailure(['required video and audio streams absent'])
 duration=float(p['format']['duration'])
 loud=loudness(video_path); lufs=float(loud['input_i']); peak=float(loud['input_tp'])
 black=_black_ratio(video_path,duration);silence=_silence_ratio(video_path,duration)
 coverage=_ass_caption_coverage(captions_ass,duration)
 failures=[]
 if abs(lufs-lufs_target)>2.0:failures.append(f'loudness {lufs:.2f} LUFS out of range')
 if peak>-1.0:failures.append(f'true peak {peak:.2f} dBTP')
 if black>.04:failures.append(f'black time {black:.2%}')
 if silence>.30:failures.append(f'silence time {silence:.2%}')
 if coverage<min_caption_coverage:failures.append(f'caption coverage {coverage:.1%}')
 warnings=['VMAF/SSIM not reported without suitable reference']
 if not forced_alignment_verified:
  warnings.insert(0,'Caption boundaries are approximate; no forced-alignment evidence')
 report=QCReport(passed=not failures,duration_s=duration,width=video['width'],height=video['height'],video_codec=video['codec_name'],audio_codec=audio['codec_name'],audio_lufs=lufs,audio_true_peak=peak,silence_ratio=silence,black_ratio=black,caption_coverage=coverage,warnings=warnings,failures=failures)
 if failures:raise QCFailure(failures,report.model_dump())
 return report
