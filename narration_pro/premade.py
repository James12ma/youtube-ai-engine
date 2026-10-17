"""Use narration made beforehand by the shared Alan7/LogicScript narrator (scripts/narrate_texts.py).

Drop-in for PiperOrEdgeNarrator.synthesize(text, path): looks the text up by hash in manifest.json and
copies the matching WAV. Refuses any text that was not narrated (no silent fallback to another voice).
"""
from __future__ import annotations
import hashlib
import json
import shutil
import wave
from pathlib import Path

from .narrator import NarrationError, SynthesisResult


class PremadeNarrator:
    def __init__(self, folder: Path):
        self.folder = Path(folder)
        man = json.loads((self.folder / 'manifest.json').read_text(encoding='utf-8'))
        self.engine = man.get('engine', 'premade')
        self.by_hash = {b['sha1']: self.folder / b['file'] for b in man['beats']}
        self.actual_backends: set[str] = set()

    def synthesize(self, text: str, output_path: Path) -> SynthesisResult:
        key = hashlib.sha1(' '.join(text.split()).encode()).hexdigest()
        src = self.by_hash.get(key)
        if src is None or not src.is_file():
            raise NarrationError('no premade narration for this text (narrate it with scripts/narrate_texts.py)')
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if src.resolve() != output_path.resolve():
            shutil.copy2(src, output_path)
        with wave.open(str(output_path), 'rb') as w:
            rate, ch, width, frames = w.getframerate(), w.getnchannels(), w.getsampwidth(), w.getnframes()
        self.actual_backends.add(self.engine)
        return SynthesisResult(wav_path=str(output_path), sample_rate=rate, channels=ch, sample_width=width,
                               duration_s=frames / rate, voice_model=self.engine, text=text)
