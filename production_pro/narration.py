"""Offline narration. Piper API uses synthesize_wav; no phoneme alignment claim."""
from __future__ import annotations
import subprocess, wave
from pathlib import Path
from .models import NarrationResult, NarrationSegment
from .errors import NarrationError

def _duration(path:Path)->float:
 p=subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(path)],text=True,capture_output=True,check=True)
 return float(p.stdout.strip())

class PiperNarrator:
    def __init__(self, model_path:Path):
        self.model_path=Path(model_path)
        if not self.model_path.is_file() or not self.model_path.with_suffix('.onnx.json').is_file():
            raise NarrationError('Piper voice requires both .onnx and .onnx.json')
    def synthesize_segments(self,texts:list[str],output_dir:Path)->NarrationResult:
        try: from piper import PiperVoice
        except ImportError as exc: raise NarrationError('Install piper-tts locally') from exc
        voice=PiperVoice.load(str(self.model_path))
        output_dir.mkdir(parents=True,exist_ok=True)
        results=[]
        for i,txt in enumerate(texts):
            out=output_dir/f'segment_{i}.wav'
            with wave.open(str(out),'wb') as fh:
                voice.synthesize_wav(txt,fh)
            results.append(NarrationSegment(text=txt,audio_path=str(out),duration_s=_duration(out)))
        return NarrationResult(segments=results,total_duration_s=sum(x.duration_s for x in results),backend='piper')

class EngineeringEspeakNarrator:
    """Never represent this robotic voice as a professional narration."""
    def synthesize_segments(self,texts:list[str],output_dir:Path)->NarrationResult:
        output_dir.mkdir(parents=True,exist_ok=True)
        results=[]
        for i,txt in enumerate(texts):
            out=output_dir/f'segment_{i}.wav'
            proc=subprocess.run(['espeak','-v','en-us','-s','147','-a','170','-w',str(out),txt],capture_output=True,text=True)
            if proc.returncode!=0: raise NarrationError(proc.stderr)
            results.append(NarrationSegment(text=txt,audio_path=str(out),duration_s=_duration(out)))
        return NarrationResult(segments=results,total_duration_s=sum(x.duration_s for x in results),backend='espeak-engineering-only')
