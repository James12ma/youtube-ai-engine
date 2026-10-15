from __future__ import annotations
import asyncio
import shutil
import subprocess
from pathlib import Path
from typing import Protocol
from .models import TTSResult, WordTiming
from .errors import TTSUnavailableError

def probe_duration(path: Path) -> float:
    p=subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(path)],capture_output=True,text=True,check=True)
    return float(p.stdout.strip())

class TTSBackend(Protocol):
    def synthesize(self,text: str,output_path: Path,voice: str | None=None) -> TTSResult: ...

class FakeTTSBackend:
    """Test ONLY: output sine tone, never a human voice."""
    def synthesize(self,text: str,output_path: Path,voice: str | None=None) -> TTSResult:
        words=text.split()
        if not words: raise TTSUnavailableError('empty narration')
        output_path.parent.mkdir(parents=True,exist_ok=True)
        duration=max(1.,len(words)/2.5)
        cmd=['ffmpeg','-y','-hide_banner','-loglevel','error','-f','lavfi','-i',f'sine=frequency=220:sample_rate=48000:duration={duration:.3f}','-af','volume=0.12','-c:a','pcm_s16le',str(output_path)]
        subprocess.run(cmd,check=True,capture_output=True)
        duration=probe_duration(output_path)
        step=duration/len(words)
        return TTSResult(audio_path=str(output_path),duration_s=duration,word_timings=[WordTiming(text=w,start_s=i*step,end_s=(i+1)*step) for i,w in enumerate(words)],voice='test-tone',backend='fake')

class EspeakOfflineBackend:
    """Real offline speech for engineering proof; robotic, NOT commercial quality.
    Timings are estimates, not timestamps from synthesizer.
    """
    def synthesize(self,text: str,output_path: Path,voice: str | None=None) -> TTSResult:
        if shutil.which('espeak') is None: raise TTSUnavailableError('espeak not installed')
        words=text.split()
        if not words: raise TTSUnavailableError('empty narration')
        output_path.parent.mkdir(parents=True,exist_ok=True)
        wav=output_path.with_suffix('.espeak.wav')
        subprocess.run(['espeak','-v',voice or 'en-us','-s','150','-w',str(wav),text],check=True,capture_output=True)
        subprocess.run(['ffmpeg','-y','-hide_banner','-loglevel','error','-i',str(wav),'-ar','48000','-ac','1','-c:a','pcm_s16le',str(output_path)],check=True,capture_output=True)
        duration=probe_duration(output_path)
        step=duration/len(words)
        return TTSResult(audio_path=str(output_path),duration_s=duration,word_timings=[WordTiming(text=w,start_s=i*step,end_s=(i+1)*step) for i,w in enumerate(words)],voice=voice or 'en-us',backend='espeak-estimated')

class EdgeTTSBackend:
    """Unofficial ONLINE Edge service. Not guaranteed free/reliable or licensed for commercial use."""
    def __init__(self,default_voice='en-US-JennyNeural'): self.default_voice=default_voice
    def synthesize(self,text: str,output_path: Path,voice: str | None=None) -> TTSResult:
        try: import edge_tts
        except ImportError as e: raise TTSUnavailableError('edge-tts not installed') from e
        chosen=voice or self.default_voice
        output_path.parent.mkdir(parents=True,exist_ok=True)
        async def run():
            audio=bytearray(); words=[]
            async for chunk in edge_tts.Communicate(text,chosen,connect_timeout=10,receive_timeout=30).stream():
                if chunk['type']=='audio': audio.extend(chunk['data'])
                elif chunk['type']=='WordBoundary':
                    start=chunk['offset']/1e7; end=start+chunk['duration']/1e7
                    words.append(WordTiming(text=chunk['text'],start_s=start,end_s=end))
            output_path.write_bytes(audio)
            return words
        try: timings=asyncio.run(run())
        except Exception as e: raise TTSUnavailableError('Edge TTS unavailable') from e
        if not output_path.exists() or output_path.stat().st_size<256: raise TTSUnavailableError('no audio')
        return TTSResult(audio_path=str(output_path),duration_s=probe_duration(output_path),word_timings=timings,voice=chosen,backend='edge-tts')
