"""Upgrade the 98s career video to local Piper narration, without rerendering visuals.

NO robotic eSpeak fallback, online services, paid APIs, uploads or publishing.
Requires the existing narration_pro Piper backend and local licensed model.
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import tempfile
import wave
from pathlib import Path

import numpy as np
from scipy.signal import resample_poly

DURATION = 98
SR = 44100
SCENES = [
    (0, 10, "Different interviews test different skills. Here are five common formats, and one smart move for each."),
    (10, 25, "One. Phone interview. The recruiter hears confidence, not body language. Stand up, smile, and keep a few notes nearby. Speak clearly and leave room for questions."),
    (25, 40, "Two. Video interview. Your camera is part of the first impression. Test the microphone, face soft natural light, and place the lens at eye level."),
    (40, 55, "Three. In-person interview. Presence counts. Arrive a little early, make natural eye contact, and bring thoughtful questions about the role."),
    (55, 70, "Four. Panel interview. You may speak with several interviewers at once. First, answer the person who asked, then include everyone with your eye contact."),
    (70, 85, "Five. Behavioral interview. Expect: tell me about a time. Use S T A R: Situation, Task, Action, Result. Finish with a measurable outcome."),
    (85, 98, "The takeaway: prepare one strong example, adapt to the interview format, and send a short thank-you afterward. Save this checklist for your next interview."),
]


def _wav_as_float(path: Path) -> tuple[np.ndarray, int]:
    with wave.open(str(path), "rb") as f:
        if f.getsampwidth() != 2:
            raise ValueError("Piper narration must be 16-bit PCM WAV")
        fs, nch = f.getframerate(), f.getnchannels()
        x = np.frombuffer(f.readframes(f.getnframes()), dtype="<i2").astype(np.float32) / 32768.0
    if nch > 1:
        x = x.reshape(-1, nch).mean(axis=1)
    return x, fs


def _bed(seconds: int) -> np.ndarray:
    """New instrumental-only bed; never reuse the old video audio with eSpeak."""
    ts = np.arange(seconds * SR, dtype=np.float32) / SR
    fade = np.minimum(np.minimum(ts / 1.4, (seconds-ts) / 1.6), 1).clip(0,1)
    arr = (.008*np.sin(2*np.pi*110*ts) + .006*np.sin(2*np.pi*164.81*ts)
           + .003*np.sin(2*np.pi*220*ts)) * fade
    for start, _, _ in SCENES[1:]:
        i = int(start * SR)
        n = int(.14 * SR)
        tt = np.arange(n) / SR
        arr[i:i+n] += .012 * np.sin(2*np.pi*350*tt) * np.exp(-tt*25)
    return arr


def _compose(voice_paths: list[Path], dest: Path) -> list[dict]:
    if len(voice_paths) != len(SCENES):
        raise ValueError("One narration WAV required per scene")
    out = _bed(DURATION)
    records = []
    for (start, end, transcript), path in zip(SCENES, voice_paths):
        voice, fs = _wav_as_float(path)
        if fs != SR:
            g = math.gcd(fs, SR)
            voice = resample_poly(voice, SR//g, fs//g)
        duration = len(voice) / SR
        max_duration = end-start-0.8
        if duration > max_duration:
            raise ValueError(
                f"Narration {start}-{end}s exceeds slot ({duration:.2f}s > {max_duration:.2f}s); "
                "rewrite or adjust timing, never truncate"
            )
        offset = int((start+.5)*SR)
        envelope = np.ones(len(voice), np.float32)
        ramp = min(int(.025*SR),len(voice)//3)
        if ramp:
            envelope[:ramp] = np.linspace(0,1,ramp)
            envelope[-ramp:] = np.linspace(1,0,ramp)
        out[offset:offset+len(voice)] += voice * envelope * 0.72
        records.append({
            "start_seconds":start,"end_seconds":end,
            "voice_seconds":round(duration,2),"text":transcript
        })
    out = np.tanh(out * 1.05).clip(-.95,.95)
    with wave.open(str(dest), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(SR)
        f.writeframes((out*32767).astype("<i2").tobytes())
    return records


def replace_voice(video: Path, model: Path, output: Path) -> dict:
    video = Path(video)
    model = Path(model)
    output = Path(output)
    if not video.is_file():
        raise FileNotFoundError(f"Source 98s MP4 not found: {video}")
    if not model.is_file() or not Path(str(model)+'.json').is_file():
        raise FileNotFoundError(
            "Offline Piper .onnx + .onnx.json model required; refusing robotic eSpeak fallback"
        )
    if video.resolve() == output.resolve():
        raise ValueError("Output must be separate from source video")
    output.parent.mkdir(parents=True, exist_ok=True)
    from narration_pro.narrator import PiperNarrator
    narrator = PiperNarrator(model_path=model, length_scale=0.96, normalize_audio=True)
    with tempfile.TemporaryDirectory(prefix="premium-narration-") as temp:
        directory = Path(temp)
        voices = []
        for i, (_, _, text) in enumerate(SCENES):
            wav = directory / f"scene_{i:02d}.wav"
            narrator.synthesize(text, wav)
            voices.append(wav)
        soundtrack = directory / "new_instrumental_plus_piper.wav"
        scenes = _compose(voices, soundtrack)
        subprocess.run([
            "ffmpeg","-hide_banner","-nostdin","-loglevel","error","-y",
            "-i",str(video),"-i",str(soundtrack),
            "-map","0:v:0","-map","1:a:0",
            "-c:v","copy","-c:a","aac","-b:a","192k",
            "-t",str(DURATION),"-movflags","+faststart",str(output)
        ], check=True)
    probe = subprocess.run([
        "ffprobe","-v","error","-show_entries","format=duration",
        "-of","default=noprint_wrappers=1:nokey=1",str(output)
    ], capture_output=True,text=True,check=True)
    duration = float(probe.stdout.strip())
    if abs(duration-DURATION) > .25:
        output.unlink(missing_ok=True)
        raise RuntimeError(f"Bad final duration: {duration:.3f}")
    report = {
        "status":"technical_pass","duration_seconds":duration,
        "narration_backend":"piper_offline","voice_model":model.name,
        "eSpeak_used":False,"scenes":scenes,"owner_approved":False,
        "auto_publish":False,"paid_services_used":False
    }
    output.with_suffix(".engine_run.json").write_text(json.dumps(report,indent=2))
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input",type=Path,required=True)
    parser.add_argument("--piper-model",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args = parser.parse_args()
    print(json.dumps(replace_voice(args.input,args.piper_model,args.output),indent=2))


if __name__ == "__main__":
    main()
