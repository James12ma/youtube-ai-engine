"""Replace the 98s career video's robotic soundtrack with existing English Chatterbox.

Reuse the ChatterboxEngine from channel/voices.py, via scripts.voice_compare._voices
(avoids importing optional channel web-app dependencies). Voice synthesis is local
once the Chatterbox model is installed and cached, but CPU rendering can be slow.

No eSpeak/Piper fallback, paid APIs, uploading, merging or publication.
The old source video's audio is discarded; its H.264 visuals are stream-copied.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from .premium_voice import DURATION, SCENES, _compose

BACKENDS = ("chatterbox-en", "chatterbox-en-mtl")


def engine_kwargs(backend: str, device: str = "cpu") -> dict:
    """Keep the Spanish Alan7 fine-tune entirely separate from English narration."""
    if backend not in BACKENDS:
        raise ValueError(f"English Chatterbox backend required: {BACKENDS}")
    if device not in ("cpu", "cuda"):
        raise ValueError("device must be cpu or cuda")
    return dict(
        reference_wav=None,         # no unauthorized voice cloning
        latam=False,                # NEVER use the Spanish LATAM fine-tune
        language="en",
        english_model=(backend == "chatterbox-en"),
        device=device,
        exaggeration=0.52,
        cfg_weight=0.35,
        temperature=0.75,
    )


def replace_with_chatterbox(
    video: Path,
    output: Path,
    *,
    backend: str = "chatterbox-en",
    device: str = "cpu",
) -> dict:
    """Render a NEW English soundtrack and retain original moving visuals.

    Fail closed if weights, dependencies, GPU/CPU resources or timings are invalid.
    Never quietly switch to eSpeak or claim a natural voice when no audio is made.
    """
    settings = engine_kwargs(backend, device)
    video, output = Path(video).resolve(), Path(output).resolve()
    if not video.is_file():
        raise FileNotFoundError(f"Source video unavailable: {video}")
    if video == output:
        raise ValueError("Never overwrite the source video")
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        raise RuntimeError("ffmpeg and ffprobe are required")
    # Heavy GPU/CPU imports and downloads must occur AFTER validating the input.
    from scripts.voice_compare import _voices
    voices = _voices()
    engine = voices.ChatterboxEngine(**settings)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="career-chatterbox-en-") as td:
        temp = Path(td)
        paths = []
        synthesis = []
        for index, (start, end, script) in enumerate(SCENES):
            wav = temp / f"scene_{index+1:02d}.wav"
            detail = voices.narrate(engine, script, wav, sentence_level=True)
            if not wav.is_file():
                raise RuntimeError(f"Chatterbox failed on scene {index+1}")
            paths.append(wav)
            synthesis.append({
                "scene": index+1,
                "backend": detail["engine"],
                "audio_seconds": detail["seconds"],
                "window_seconds": end-start,
            })
        mixed = temp / "soundtrack.wav"
        timing = _compose(paths, mixed)  # refuses overflow; no truncation, no speed hacks
        draft = temp / "new_voice.mp4"
        subprocess.run([
            "ffmpeg", "-hide_banner", "-nostdin", "-loglevel", "error", "-y",
            "-i", str(video), "-i", str(mixed),
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-t", str(DURATION), "-movflags", "+faststart", str(draft),
        ], check=True)
        p = subprocess.run([
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(draft),
        ], capture_output=True, text=True, check=True)
        duration = float(p.stdout.strip())
        if abs(duration-DURATION) > 0.25:
            raise RuntimeError(f"Unexpected MP4 duration {duration:.3f}s")
        # Copy to a temp file beside output, then atomically replace. The
        # working temp dir and destination may be on different filesystems.
        with tempfile.NamedTemporaryFile(dir=output.parent, prefix=".chatterbox-",
                                         suffix=".mp4", delete=False) as fh:
            staged = Path(fh.name)
        try:
            shutil.copyfile(draft, staged)
            staged.replace(output)
        finally:
            staged.unlink(missing_ok=True)
    report = {
        "status": "technical_pass_owner_review_pending",
        "duration_seconds": round(duration, 3),
        "backend": backend,
        "model": engine.loaded,
        "language": "en",
        "original_espeak_audio_removed": True,
        "voice_cloning": False,
        "synthesis": synthesis,
        "timing": timing,
        "owner_approved": False,
        "auto_publish": False,
        "paid_service_used": False,
    }
    output.with_suffix(".engine_run.json").write_text(json.dumps(report, indent=2))
    return report



def sample_english_voice(
    output: Path, *, backend: str = "chatterbox-en", device: str = "cpu"
) -> dict:
    """Generate a short English voice audition before scheduling a 98s render.

    Runs the same existing English Chatterbox as the full movie. No video
    rendering, no upload, no robotics fallback. Audio stays unapproved.
    """
    settings = engine_kwargs(backend, device)
    from scripts.voice_compare import _voices
    voices = _voices()
    engine = voices.ChatterboxEngine(**settings)
    output = Path(output).resolve()
    if output.suffix.lower() != ".wav":
        raise ValueError("Sample output must be a .wav file")
    output.parent.mkdir(parents=True, exist_ok=True)
    detail = voices.narrate(engine, SCENES[0][2], output, sentence_level=True)
    return {
        "status": "voice_audition_owner_review_pending",
        "backend": backend,
        "language": "en",
        "model": engine.loaded,
        "seconds": detail["seconds"],
        "sample": str(output),
        "owner_approved": False,
        "auto_publish": False,
        "paid_service_used": False,
    }

def main() -> None:
    parser = argparse.ArgumentParser(description="Revoice the existing 98s video with English Chatterbox")
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--sample-out", type=Path,
                        help="10s-ish English voice audition WAV only; no video")
    parser.add_argument("--backend", choices=BACKENDS, default="chatterbox-en")
    parser.add_argument("--device", choices=("cpu","cuda"), default="cpu")
    args = parser.parse_args()
    if args.sample_out is not None:
        if args.input is not None or args.output is not None:
            parser.error("--sample-out cannot be combined with --input/--output")
        result=sample_english_voice(args.sample_out, backend=args.backend, device=args.device)
    else:
        if args.input is None or args.output is None:
            parser.error("--input and --output are required for full video")
        result=replace_with_chatterbox(args.input, args.output,
                                       backend=args.backend, device=args.device)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
