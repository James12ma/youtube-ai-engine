"""Reuse the same prepared voice packets as Alan7, without another TTS engine.

Compatible with scripts/narrate_beats.py on main (911c4bb). A packet for
English MUST declare language='en'; legacy Alan7 packets are Spanish only.
This is an input adapter, not evidence of voice naturalness or forced alignment.
"""
from __future__ import annotations
import hashlib
import json
import shutil
import wave
from pathlib import Path
from .narrator import NarrationError, SynthesisResult


class PreparedNarrator:
    def __init__(self, folder: Path, *, language: str):
        self.folder=Path(folder)
        self.manifest=json.loads((self.folder/'manifest.json').read_text())
        declared=self.manifest.get('language','es')  # existing Alan7 contract
        if language not in ('en','es') or declared!=language:
            raise NarrationError('Prepared voice language does not match the lesson; never reuse Spanish audio for English')
        self.language=language
        self.attribution=self.manifest.get('attribution')
        self.index=0
        self.actual_backends=set()

    def synthesize(self, text: str, output_path: Path) -> SynthesisResult:
        text=' '.join(text.split())
        rows=self.manifest.get('beats',[])
        if self.index>=len(rows):raise NarrationError('Prepared voice packet has too few chapters')
        row=rows[self.index]
        if row.get('index',self.index)!=self.index or row.get('sha1')!=hashlib.sha1(text.encode()).hexdigest():
            raise NarrationError('Prepared voice text does not match this chapter')
        source=self.folder/f'beat_{self.index}.wav'
        try:
            with wave.open(str(source),'rb') as w:
                rate, channels, width, frames=w.getframerate(),w.getnchannels(),w.getsampwidth(),w.getnframes()
            duration=frames/rate
        except (OSError,wave.Error,ZeroDivisionError) as e:
            raise NarrationError('Invalid prepared chapter WAV') from e
        if duration<=0 or abs(duration-float(row['seconds']))>.15:
            raise NarrationError('Prepared audio duration does not match its manifest')
        if row.get('audio_sha256') and hashlib.sha256(source.read_bytes()).hexdigest()!=row['audio_sha256']:
            raise NarrationError('Prepared audio hash mismatch')
        output_path=Path(output_path);output_path.parent.mkdir(parents=True,exist_ok=True)
        if source.resolve()!=output_path.resolve():shutil.copyfile(source,output_path)
        backend=self.manifest.get('engine','prepared-unknown')
        self.actual_backends.add(backend)
        self.index+=1
        return SynthesisResult(wav_path=str(output_path),sample_rate=rate,channels=channels,sample_width=width,
                               duration_s=duration,voice_model=backend+':'+self.manifest.get('model','unspecified'),text=text)
