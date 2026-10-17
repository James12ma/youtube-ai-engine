"""Opt-in mastering shared by documentary and software lessons.

Reuses the existing local narrator, compositor, caption burner and EBU normalizer.
It does not acquire footage, select a channel, grant approval, or upload anything.
Naturalness and picture relevance still need editorial review; LUFS is not taste.
"""
from __future__ import annotations

import json
import math
import subprocess
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Literal

from narration_pro import PiperOrEdgeNarrator, normalize_loudness
from production_pro.editing import burn_captions
from production.audio import loudness


@dataclass(frozen=True)
class QualityProfile:
    mode: Literal['screen', 'documentary']
    language: Literal['en', 'es']
    width: int = 1920
    height: int = 1080
    fps: int = 24
    target_lufs: float = -16.0
    true_peak: float = -2.0  # margin for AAC intersample peaks

    def __post_init__(self):
        if self.mode not in ('screen', 'documentary') or self.language not in ('en', 'es'):
            raise ValueError('Unknown production mode/language')
        if self.width < 1920 or self.height < 1080 or self.width % 2 or self.height % 2:
            raise ValueError('Final quality requires native 1080p or higher, with even dimensions')
        if self.fps not in (24, 25, 30, 50, 60):
            raise ValueError('Unsupported frame rate')


def local_narrator(model: Path, profile: QualityProfile):
    """Same neural backend in both modes; no automatic online fallback.

    A language-specific model is explicit. Claude's future engine can implement
    the existing synthesize(text, path) contract without another renderer.
    """
    config = json.loads(Path(str(model)+'.json').read_text())
    code = config.get('language', {}).get('code', '')
    if not code.startswith(profile.language):
        raise ValueError('Voice model language does not match the channel profile')
    pace = 1.03 if profile.mode == 'screen' else 1.08
    return PiperOrEdgeNarrator(model, length_scale=pace, allow_edge_fallback=False)


def _run(args):
    proc = subprocess.run(args, capture_output=True, text=True)
    if proc.returncode:
        raise RuntimeError('Media operation failed: '+proc.stderr[-1000:])
    return proc


def probe(path: Path) -> dict:
    return json.loads(_run(['ffprobe', '-v', 'error', '-show_streams', '-show_format',
                            '-of', 'json', str(path)]).stdout)


def mix_audio(voice: Path, out: Path, *, music: Path | None = None,
              profile: QualityProfile) -> dict:
    """Sidechain-duck optional owner-cleared music, fade the bed, then normalize.

    The voice is never sped up to fit a picture. Normalization happens AFTER
    mixing, and the encoded result is measured again by audit_video.
    """
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    normalized = out.with_name(out.stem+'_voice.wav')
    normalize_loudness(voice, normalized, target_lufs=profile.target_lufs, true_peak=profile.true_peak)
    duration = float(probe(normalized)['format']['duration'])
    raw = out.with_name(out.stem+'_raw.wav')
    if music:
        filters = (
            '[0:a]aformat=channel_layouts=stereo,asplit=2[v][side];'
            '[1:a]aresample=48000,aformat=channel_layouts=stereo,'
            f'volume=0.12,afade=t=in:d=0.6,afade=t=out:st={max(0,duration-1):.3f}:d=1[bed];'
            '[bed][side]sidechaincompress=threshold=0.025:ratio=8:attack=20:release=350[duck];'
            '[v][duck]amix=inputs=2:duration=first:normalize=0[m]')
        _run(['ffmpeg', '-y', '-v', 'error', '-i', str(normalized), '-stream_loop', '-1',
              '-i', str(music), '-filter_complex', filters, '-map', '[m]', '-t', str(duration),
              '-ar', '48000', '-c:a', 'pcm_s16le', str(raw)])
    else:
        _run(['ffmpeg', '-y', '-v', 'error', '-i', str(normalized), '-ac', '2',
              '-c:a', 'pcm_s16le', str(raw)])
    report = normalize_loudness(raw, out, target_lufs=profile.target_lufs, true_peak=profile.true_peak)
    return {'normalization': report.model_dump(), 'sidechain_ducking': bool(music),
            'music_source': str(music) if music else None, 'voice_duration_s': duration}


def master_video(picture: Path, voice: Path, out: Path, *, profile: QualityProfile,
                 music: Path | None = None, captions: Path | None = None) -> dict:
    """Common final encode; existing documentary/screen renderers keep their own edit.

    Refuse undersized pictures and timeline mismatch, instead of hiding either
    with upscaling, freeze frames, looping a lesson, or -shortest truncation.
    """
    info = probe(picture)
    video = next(s for s in info['streams'] if s['codec_type']=='video')
    if video['width'] < profile.width or video['height'] < profile.height:
        raise ValueError('Source picture is below the requested native resolution')
    video_s = float(video.get('duration', info['format']['duration']))
    voice_s = float(probe(voice)['format']['duration'])
    if abs(video_s-voice_s) > 0.25:
        raise ValueError('Picture/voice timeline mismatch; do not trim an unshown action or spoken word')
    out.parent.mkdir(parents=True, exist_ok=True)
    mixed = out.with_name(out.stem+'_mix.wav')
    audio_report = mix_audio(voice, mixed, music=music, profile=profile)
    target = out.with_name(out.stem+'_uncaptioned.mp4') if captions else out
    _run(['ffmpeg', '-y', '-v', 'error', '-i', str(picture), '-i', str(mixed),
          '-map', '0:v:0', '-map', '1:a:0', '-vf',
          f'scale={profile.width}:{profile.height}:flags=lanczos,fps={profile.fps},setsar=1',
          '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18', '-pix_fmt', 'yuv420p',
          '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-movflags', '+faststart', str(target)])
    if captions:
        burn_captions(target, captions, out)
    report = audit_video(out, profile=profile)
    return {**report, 'audio_mix': audio_report, 'captions': str(captions) if captions else None}


def audit_video(path: Path, *, profile: QualityProfile, screen_actions: list[dict] | None = None,
                documentary_report: dict | None = None) -> dict:
    """Technical checks plus DIFFERENT evidence checks for the two modes.

    Missing evidence is unverified, never silently marked passed. This cannot
    infer picture relevance or voice naturalness from a valid MP4 container.
    """
    p = probe(path)
    v = next(s for s in p['streams'] if s['codec_type']=='video')
    a = next(s for s in p['streams'] if s['codec_type']=='audio')
    issues = []
    if (v['width'], v['height']) != (profile.width, profile.height):
        issues.append('resolution')
    if v['codec_name']!='h264' or v['pix_fmt']!='yuv420p' or a['codec_name']!='aac':
        issues.append('encoding')
    if Fraction(v['r_frame_rate']) != profile.fps or Fraction(v['avg_frame_rate']) != profile.fps:
        issues.append('frame_rate')
    if abs(float(v['duration'])-float(a['duration'])) > .25:
        issues.append('av_duration')
    measure = loudness(path)
    lufs, peak = float(measure['input_i']), float(measure['input_tp'])
    if not math.isfinite(lufs) or abs(lufs-profile.target_lufs) > 1.5 or peak > -1:
        issues.append('loudness_or_peak')
    _run(['ffmpeg', '-v', 'error', '-i', str(path), '-f', 'null', '-'])
    evidence = None
    if profile.mode == 'screen' and screen_actions is not None:
        required = {'move', 'click', 'type', 'menu', 'scroll'}
        kinds = {x['action']['do'] for x in screen_actions}
        checks = [x.get('observed', {}).get(ref)==value for x in screen_actions
                  for ref, value in x['action'].get('expect', {}).items()]
        evidence = {'passed': required <= kinds and bool(checks) and all(checks),
                    'missing_interactions': sorted(required-kinds), 'live_cell_checks': len(checks)}
    if profile.mode == 'documentary' and documentary_report is not None:
        shots = documentary_report.get('shots', [])
        visual = documentary_report.get('visual_qa')
        evidence = {'footage_rendered': bool(shots), 'shot_count': len(shots),
                    'license_gate': documentary_report.get('license_gate'),
                    'visual_qa': visual,
                    'passed': bool(shots) and bool(visual and visual.get('passed'))}
    return {'technical_passed': not issues, 'issues': issues, 'mode': profile.mode,
            'resolution': f"{v['width']}x{v['height']}", 'fps': v['avg_frame_rate'],
            'duration_s': float(p['format']['duration']), 'lufs': lufs, 'true_peak': peak,
            'decode_passed': True, 'mode_evidence': evidence,
            'editorial_review_required': True, 'ready_for_publication': False}
