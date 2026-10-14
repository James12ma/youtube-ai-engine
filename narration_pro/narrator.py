"""Piper 1.8: CPU WAV synthesis. No model download or paid calls here."""
from __future__ import annotations

import wave
from pathlib import Path
from typing import Any
from pydantic import BaseModel, Field

DEFAULT_VOICE = "en_US-libritts-high"

class NarrationError(RuntimeError):
    pass

class SynthesisResult(BaseModel):
    wav_path: str
    sample_rate: int = Field(gt=0)
    channels: int = Field(gt=0)
    sample_width: int = Field(gt=0)
    duration_s: float = Field(gt=0)
    voice_model: str
    text: str

class PiperNarrator:
    def __init__(self, model_path: Path, config_path: Path | None = None, *,
                 length_scale: float = 1.0, noise_scale: float = 0.667,
                 noise_w_scale: float = 0.8, volume: float = 1.0,
                 normalize_audio: bool = False, voice: Any | None = None):
        self.model_path = Path(model_path)
        self.config_path = Path(config_path) if config_path else Path(str(model_path)+".json")
        self._voice = voice
        if voice is None and (not self.model_path.is_file() or not self.config_path.is_file()):
            raise NarrationError("Piper voice needs .onnx and .onnx.json files: " + str(model_path))
        if not 0.3 <= length_scale <= 3 or not 0 < volume <= 2:
            raise NarrationError("invalid Piper pacing/volume")
        self.settings = dict(length_scale=length_scale, noise_scale=noise_scale,
                             noise_w_scale=noise_w_scale, volume=volume,
                             normalize_audio=normalize_audio)

    def _load(self):
        if self._voice is not None:
            return self._voice
        try:
            from piper import PiperVoice
        except ImportError as exc:
            raise NarrationError("piper-tts==1.8.0 required") from exc
        self._voice = PiperVoice.load(str(self.model_path), config_path=str(self.config_path), use_cuda=False)
        return self._voice

    def synthesize(self, text: str, output_path: Path) -> SynthesisResult:
        if not text or not text.strip():
            raise NarrationError("empty transcript")
        voice = self._load()
        try:
            from piper import SynthesisConfig
        except ImportError as exc:
            raise NarrationError("piper-tts==1.8.0 required") from exc
        cfg = SynthesisConfig(**self.settings)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with wave.open(str(output_path), "wb") as out:
                voice.synthesize_wav(text, out, syn_config=cfg)
        except Exception as exc:
            output_path.unlink(missing_ok=True)
            raise NarrationError("Piper synthesis failed: " + type(exc).__name__) from exc
        try:
            with wave.open(str(output_path), "rb") as wav:
                rate, ch, width, nframes = wav.getframerate(), wav.getnchannels(), wav.getsampwidth(), wav.getnframes()
        except Exception as exc:
            raise NarrationError("Piper output invalid WAV") from exc
        if min(rate, ch, width, nframes) <= 0:
            raise NarrationError("Piper produced empty or malformed WAV")
        return SynthesisResult(wav_path=str(output_path), sample_rate=rate, channels=ch,
                               sample_width=width, duration_s=nframes/rate,
                               voice_model=str(self.model_path), text=text)
