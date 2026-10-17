"""Footage mode: documentary edits built from REAL licensed wildlife clips.

A plan (JSON) lists narration beats; each beat names the clip segments shown
while it is spoken. Every clip is re-checked on Wikimedia Commons at render
time (PD / CC0 / CC BY only, no Restrictions) and credited. Locations are
labelled on screen so unrelated clips are never presented as one family or
one place.

AI clips are accepted by the architecture for later projects, but only as
local files with ``"ai_generated": true`` and a visible disclosure label that
is burned into every frame where they appear. Nothing here calls a paid API.

The output is a review sample: nothing is uploaded or published.
"""
from __future__ import annotations
import json
import re
import subprocess
import textwrap
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse
from pydantic import BaseModel, Field, field_validator, model_validator

FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
FONT_BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
AI_LABEL = 'Recreación generada con IA — no son imágenes reales'


class DocumentaryError(RuntimeError):
    pass


class ClipSource(BaseModel):
    kind: Literal['commons', 'pixabay', 'ai'] = 'commons'
    title: str = ''            # exact Commons File: title (kind=commons)
    pixabay_id: int | None = None
    species_verified: bool = False   # set only after someone looked at the clip (tags are not proof)
    ai_checked: bool = False         # set only after the Pixabay page was checked for an AI-generated label
    path: str = ''             # local file (kind=ai)
    ai_generated: bool = False
    location: str = ''         # where it was filmed, as stated by the source
    disclosure: str = ''       # on-screen label for AI clips

    @model_validator(mode='after')
    def _check(self):
        if self.kind == 'commons' and not self.title.startswith('File:'):
            raise ValueError('commons clip needs an exact File: title')
        if self.kind == 'ai':
            if not self.ai_generated:
                raise ValueError('ai clips must set ai_generated=true')
            if not self.path:
                raise ValueError('ai clips need a local path')
            self.disclosure = self.disclosure or AI_LABEL
        if self.kind == 'pixabay' and (self.pixabay_id is None or self.ai_generated):
            raise ValueError('pixabay clips need pixabay_id and must be real footage')
        if self.kind == 'commons' and self.ai_generated:
            raise ValueError('commons clips in footage mode must be real footage')
        return self


class Shot(BaseModel):
    clip: str
    in_s: float = Field(ge=0)
    out_s: float
    label: str = ''            # usually the filming location
    note: str = ''             # what the shot shows (for the QA report)
    key_s: float | None = None  # moment of the key action; the used segment is placed around it

    @model_validator(mode='after')
    def _order(self):
        if self.out_s - self.in_s < 1.5:
            raise ValueError('shot window must be at least 1.5 s')
        if self.key_s is not None and not self.in_s <= self.key_s <= self.out_s:
            raise ValueError('key_s must lie inside the shot window')
        return self


def segment_start(shot: 'Shot', length: float, slack: float = 0.6) -> float:
    """Where to start a ``length``-second cut inside the window, placing key_s 40 % in."""
    if shot.key_s is None:
        return shot.in_s
    start = shot.key_s - 0.4 * length
    return max(shot.in_s, min(start, shot.out_s + slack - length))


class Beat(BaseModel):
    narration: str
    shots: list[Shot] = Field(min_length=1)
    overlay: str = ''          # optional on-screen note for the whole beat
    sources: list[str] = Field(default_factory=list)  # fact sources for this narration

    @field_validator('narration')
    @classmethod
    def _text(cls, v):
        if not v.strip():
            raise ValueError('empty narration')
        return ' '.join(v.split())


class DocumentaryPlan(BaseModel):
    series: str
    title: str
    subtitle: str = ''
    language: Literal['es', 'en'] = 'es'
    clips: dict[str, ClipSource]
    beats: list[Beat] = Field(min_length=1)
    preroll_s: float = Field(default=2.5, ge=0, le=6)
    pause_s: float = Field(default=0.6, ge=0, le=2)
    tail_s: float = Field(default=1.2, ge=0, le=4)
    credits_s: float = Field(default=5.0, ge=3, le=12)
    crossfade_s: float = Field(default=0.5, ge=0, le=1.0)
    ambience: list[str] = Field(default_factory=list)  # Commons audio search terms (optional)
    credits_note: str = ''
    title_start_s: float = Field(default=0.4, ge=0, le=20)
    show_title: bool = True
    voice_length_scale: float = Field(default=1.0, ge=0.8, le=1.4)  # >1 = slower, calmer narration
    # Spoken-only phonetic fixes (Piper [[ IPA ]] syntax); subtitles keep the normal spelling.
    pronunciations: dict[str, str] = Field(default_factory=dict)     # voice / fact sources line for the credits card

    @model_validator(mode='after')
    def _refs(self):
        for beat in self.beats:
            for shot in beat.shots:
                if shot.clip not in self.clips:
                    raise ValueError('unknown clip id: ' + shot.clip)
        return self


def load_plan(path: Path) -> DocumentaryPlan:
    return DocumentaryPlan.model_validate_json(Path(path).read_text(encoding='utf-8'))


def allocate(seconds: float, shots: list[Shot]) -> list[float]:
    """Split a beat's on-screen time across its shots, proportional to each window.

    Never asks a shot for more footage than its window holds: if the beat is
    longer than all windows together, that is a plan error (we do not loop or
    freeze footage to fill time).
    """
    windows = [s.out_s - s.in_s for s in shots]
    if seconds > sum(windows) + 1e-6:
        raise DocumentaryError(f'beat needs {seconds:.1f}s but its shots only hold {sum(windows):.1f}s')
    total = sum(windows)
    return [seconds * w / total for w in windows]


def timeline(plan: DocumentaryPlan, beat_audio_s: list[float]) -> dict:
    """Narration start times and per-shot durations for the whole edit."""
    if len(beat_audio_s) != len(plan.beats):
        raise DocumentaryError('one narration clip per beat required')
    starts, shots = [], []
    t = plan.preroll_s
    for i, (beat, audio) in enumerate(zip(plan.beats, beat_audio_s)):
        starts.append(t)
        span = audio + (plan.pause_s if i < len(plan.beats) - 1 else plan.tail_s)
        if i == 0:
            span += plan.preroll_s           # the first beat's footage also covers the pre-roll
        for shot, d in zip(beat.shots, allocate(span, beat.shots)):
            shots.append({'beat': i, 'shot': shot, 'seconds': d})
        t += audio + (plan.pause_s if i < len(plan.beats) - 1 else plan.tail_s)
    return {'narration_starts': starts, 'shots': shots, 'footage_s': t, 'total_s': t + plan.credits_s}


def license_gate(plan: 'DocumentaryPlan', clip_info: dict[str, dict]) -> dict:
    """Publication gate: every clip must have a confirmed licence and (for Pixabay) checked species/AI status."""
    issues = []
    for cid, src in plan.clips.items():
        info = clip_info.get(cid, {})
        if src.kind == 'commons' and info.get('license_review_pending', True):
            issues.append(f'{cid}: Commons licence review pending (verify the original source page)')
        if src.kind == 'pixabay':
            if not src.species_verified:
                issues.append(f'{cid}: species not verified')
            if not src.ai_checked:
                issues.append(f'{cid}: Pixabay page not checked for an AI-generated label')
        if src.kind == 'ai':
            issues.append(f'{cid}: AI clip — needs YouTube altered/synthetic disclosure')
    return {'passed': not issues, 'issues': issues}


def credit_lines(clips: dict[str, dict], ambience: dict | None, voice_note: str) -> list[str]:
    lines = []
    for info in clips.values():
        if info.get('ai_generated'):
            lines.append(f"Imágenes: {AI_LABEL}.")
            continue
        if info.get('source') == 'pixabay':
            lines.append(f"Pixabay #{info['id']} — {info['author']} — {info['license']} — pixabay.com. "
                         'Cambios: recortado, reencuadrado a 16:9, texto añadido.')
            continue
        name = info['title'].removeprefix('File:').rsplit('.', 1)[0]
        lines.append(f"«{name}» — {info['author']} — {info['license']} ({info['license_url']}) — Wikimedia Commons. "
                     'Cambios: recortado, reencuadrado a 16:9, texto añadido.')
    if ambience:
        name = ambience['title'].removeprefix('File:').rsplit('.', 1)[0]
        lines.append(f"Sonido de ambiente: «{name}» — {ambience['author']} — {ambience['license']} — Wikimedia Commons. "
                     'No fue grabado en los lugares mostrados.')
    lines.append(voice_note)
    return lines


def spoken_text(text: str, pronunciations: dict[str, str]) -> str:
    """Replace whole words with explicit phonemes for the voice only (longest words first)."""
    for word in sorted(pronunciations, key=len, reverse=True):
        text = re.sub(r'(?<![\w\[])' + re.escape(word) + r'(?![\w\]])', '[[ ' + pronunciations[word] + ' ]]', text)
    return text


# ---------------------------------------------------------------- rendering

def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode:
        raise DocumentaryError('FFmpeg error: ' + p.stderr[-800:])
    return p


def _duration(path: Path) -> float:
    p = _run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(path)])
    return float(p.stdout.strip())


def _textfile(work: Path, name: str, text: str) -> str:
    f = work / name
    f.write_text(text, encoding='utf-8')
    return str(f.resolve()).replace('\\', '\\\\').replace(':', '\\:').replace("'", "\\'")


def _cut_shot(src: Path, shot: Shot, seconds: float, out: Path, work: Path, idx: int, *,
              width: int, height: int, fps: int, label: str, disclosure: str) -> None:
    vf = [f'scale={width}:{height}:force_original_aspect_ratio=increase:flags=lanczos',
          f'crop={width}:{height}', f'fps={fps}', 'format=yuv420p']
    if label:
        tf = _textfile(work, f'label_{idx}.txt', label)
        vf.append(f"drawtext=fontfile={FONT}:textfile='{tf}':x=56:y=48:fontsize=42:fontcolor=white:borderw=2:bordercolor=black@0.6:"
                  'shadowcolor=black@0.7:shadowx=2:shadowy=2:'
                  f"alpha='min(1,max(0,(t-0.3)/0.5))*min(1,max(0,({seconds:.3f}-0.4-t)/0.5))'")
    if disclosure:   # AI clips: label on every frame, never fading out
        tf = _textfile(work, f'ai_{idx}.txt', disclosure)
        vf.append(f"drawtext=fontfile={FONT_BOLD}:textfile='{tf}':x=(w-tw)/2:y=h-140:fontsize=34:"
                  'fontcolor=white:box=1:boxcolor=black@0.65:boxborderw=14')
    _run(['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error', '-ss', f'{shot.in_s:.3f}', '-t', f'{seconds:.3f}',
          '-i', str(src), '-an', '-vf', ','.join(vf), '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '17',
          str(out)])
    got = _duration(out)
    if got < seconds - 0.15:
        raise DocumentaryError(f'shot {idx} too short in source: wanted {seconds:.2f}s, got {got:.2f}s')


def _credits_card(lines: list[str], series: str, out: Path, *, width: int, height: int) -> None:
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new('RGB', (width, height), (8, 14, 22))
    d = ImageDraw.Draw(img)
    head = ImageFont.truetype(FONT_BOLD, 46)
    d.text((110, 90), series.upper() + ' — CRÉDITOS', font=head, fill=(235, 235, 235))
    size = 25
    while size >= 16:
        body = ImageFont.truetype(FONT, size)
        chars = int((width - 220) / (size * 0.56))
        wrapped = [textwrap.wrap(line, chars) for line in lines]
        need = sum(len(w) for w in wrapped) * int(size * 1.35) + len(lines) * int(size * 0.6)
        if need <= height - 260:
            break
        size -= 1
    y = 190
    for w in wrapped:
        for row in w:
            d.text((110, y), row, font=body, fill=(205, 212, 220))
            y += int(size * 1.35)
        y += int(size * 0.6)
    img.save(out)


def _xfade_chain(parts: list[Path], seconds: list[float], fade: float, out: Path, fps: int) -> None:
    """Dissolve between parts; part i was rendered fade seconds longer so totals stay exact."""
    inputs = []
    for p in parts:
        inputs += ['-i', str(p)]
    if len(parts) == 1:
        _run(['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error', *inputs, '-c', 'copy', str(out)])
        return
    filters, prior, offset = [], '0:v', 0.0
    for i in range(1, len(parts)):
        offset += seconds[i - 1]
        label = f'v{i}'
        filters.append(f'[{prior}][{i}:v]xfade=transition=fade:duration={fade:.3f}:offset={offset:.3f}[{label}]')
        prior = label
    _run(['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error', *inputs, '-filter_complex', ';'.join(filters),
          '-map', f'[{prior}]', '-r', str(fps), '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '17',
          '-pix_fmt', 'yuv420p', str(out)])


def search_ambience(client, terms: list[str]) -> dict | None:
    """A free-licensed natural sea/ocean recording on Commons, or None."""
    from channel.commons import API, USER_AGENT, _clean, license_allowed
    good = re.compile(r'wave|ocean|sea|surf|shore|beach|ola|mar\b', re.I)
    bad = re.compile(r'music|song|voice|speech|radio|synth|remix|loop|electronic|\bai\b|generated', re.I)
    for t in terms:
        r = client.get(API, params={'action': 'query', 'format': 'json', 'formatversion': '2', 'generator': 'search',
                                    'gsrsearch': f'filetype:audio {t}', 'gsrnamespace': '6', 'gsrlimit': '30',
                                    'prop': 'videoinfo', 'viprop': 'url|size|mime|extmetadata|mediatype'},
                       headers={'User-Agent': USER_AGENT}, timeout=30)
        r.raise_for_status()
        pages = sorted(r.json().get('query', {}).get('pages', []), key=lambda p: p.get('index', 999))
        for page in pages:
            info = (page.get('videoinfo') or [{}])[0]
            meta = info.get('extmetadata') or {}
            lic = _clean((meta.get('LicenseShortName') or {}).get('value'))
            desc = _clean((meta.get('ImageDescription') or {}).get('value'))
            title = page.get('title', '')
            url = info.get('url') or ''
            if ((info.get('mediatype') or '').upper() != 'AUDIO' or not license_allowed(lic)
                    or _clean((meta.get('Restrictions') or {}).get('value'))
                    or not good.search(title) or bad.search(title + ' ' + desc)
                    or float(info.get('duration') or 0) < 20 or int(info.get('size') or 0) > 60_000_000
                    or urlparse(url).hostname != 'upload.wikimedia.org'):
                continue
            return {'title': title, 'license': lic, 'author': _clean((meta.get('Artist') or {}).get('value')) or 'Unknown author',
                    'license_url': _clean((meta.get('LicenseUrl') or {}).get('value')), 'description': desc[:300],
                    'page': info.get('descriptionurl') or '', 'duration_s': float(info.get('duration') or 0),
                    'download': url, 'search_terms': t}
    return None


def render_documentary(plan: DocumentaryPlan, voice_model: Path, out: Path, *, width: int = 1920,
                       height: int = 1080, fps: int = 24, clip_files: dict[str, Path] | None = None,
                       clip_info: dict[str, dict] | None = None, ambience: dict | None = None,
                       ambience_file: Path | None = None) -> dict:
    """Render the sample. ``clip_files``/``clip_info`` come from the Commons download step."""
    from narration_pro import (PiperOrEdgeNarrator, WhisperXAligner, normalize_loudness, build_ass_from_words,
                               assess_caption_quality, save_word_timestamps, save_srt_from_blocks)
    from production_pro.editing import burn_captions
    out = Path(out)
    work = out.parent / (out.stem + '_work')
    work.mkdir(parents=True, exist_ok=True)
    clip_files = dict(clip_files or {})
    clip_info = dict(clip_info or {})
    for cid, src in plan.clips.items():
        if src.kind == 'ai':
            clip_files[cid] = Path(src.path)
            clip_info[cid] = {'title': src.path, 'ai_generated': True}
        if cid not in clip_files or not Path(clip_files[cid]).is_file():
            raise DocumentaryError('missing footage for clip ' + cid)

    # 1. narration, one WAV per beat (real Piper voice; no fallback service)
    narrator = PiperOrEdgeNarrator(voice_model, allow_edge_fallback=False, length_scale=plan.voice_length_scale)
    wavs = [narrator.synthesize(spoken_text(b.narration, plan.pronunciations), work / f'beat_{i}.wav')
            for i, b in enumerate(plan.beats)]
    tl = timeline(plan, [w.duration_s for w in wavs])
    total = tl['total_s']

    # 2. voice track: each beat placed at its start time, silence elsewhere
    inputs, mix = [], []
    for i, (w, start) in enumerate(zip(wavs, tl['narration_starts'])):
        inputs += ['-i', w.wav_path]
        ms = int(round(start * 1000))
        mix.append(f'[{i}:a]aresample=48000,aformat=channel_layouts=mono,adelay={ms}|{ms}[a{i}]')
    mix.append(''.join(f'[a{i}]' for i in range(len(wavs))) + f'amix=inputs={len(wavs)}:normalize=0,'
               f'apad,atrim=0:{total:.3f}[voice]')
    raw = work / 'voice_raw.wav'
    _run(['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error', *inputs, '-filter_complex', ';'.join(mix),
          '-map', '[voice]', '-ac', '1', '-ar', '48000', '-c:a', 'pcm_s16le', str(raw)])
    voice = work / 'voice_norm.wav'
    loud = normalize_loudness(raw, voice)

    # 3. forced-aligned Spanish subtitles (no proportional guessing)
    transcript = ' '.join(b.narration for b in plan.beats)
    aligned = WhisperXAligner(language=plan.language, device='cpu', min_token_coverage=.98).align(voice, transcript)
    save_word_timestamps(aligned, work / 'words.json')
    ass = work / 'captions.ass'
    count, blocks = build_ass_from_words(aligned.words, ass, width=width, height=height, animated=False, size=64,
                                         max_chars_per_line=32, bottom_margin=70, max_duration_s=3.2)
    caption_qc = assess_caption_quality(aligned.words, blocks, aligned.duration_s, min_coverage=.98)
    if not caption_qc.passed:
        raise DocumentaryError('Forced captions failed QC: ' + repr(caption_qc.failures))
    srt = save_srt_from_blocks(blocks, out.with_suffix('.srt'))

    # 4. picture: cut every shot (with location label), dissolve between them
    fade = plan.crossfade_s
    parts, secs, shot_report = [], [], []
    shots = tl['shots']
    for i, item in enumerate(shots):
        shot, d = item['shot'], item['seconds']
        src = plan.clips[shot.clip]
        render_len = d + (fade if i < len(shots) - 1 or plan.credits_s else 0)
        shot = shot.model_copy(update={'in_s': segment_start(shot, render_len)})
        if shot.in_s + render_len > shot.out_s + 0.6:   # dissolve tail may borrow up to 0.6 s past the window
            raise DocumentaryError(f'shot {i} ({shot.clip}) window too short for {render_len:.2f}s')
        p = work / f'shot_{i:02d}.mp4'
        _cut_shot(Path(clip_files[shot.clip]), shot, render_len, p, work, i, width=width, height=height, fps=fps,
                  label=shot.label, disclosure=src.disclosure if src.kind == 'ai' else '')
        parts.append(p)
        secs.append(d)
        shot_report.append({'index': i, 'beat': item['beat'], 'clip': shot.clip,
                            'source_title': clip_info.get(shot.clip, {}).get('title'),
                            'source_in_s': shot.in_s, 'source_out_s': round(shot.in_s + d, 2),
                            'seconds': round(d, 2), 'label': shot.label, 'note': shot.note,
                            'ai_generated': src.kind == 'ai'})
    voice_note = plan.credits_note or 'Narración: voz sintética (Piper). Muestra de revisión — no publicada.'
    credits = work / 'credits.png'
    lines = credit_lines({c: clip_info[c] for c in plan.clips}, ambience, voice_note)
    _credits_card(lines, plan.series, credits, width=width, height=height)
    cpart = work / 'credits.mp4'
    _run(['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error', '-loop', '1', '-t', f'{plan.credits_s:.3f}',
          '-i', str(credits), '-vf', f'fps={fps},format=yuv420p', '-c:v', 'libx264', '-preset', 'veryfast',
          '-crf', '17', str(cpart)])
    parts.append(cpart)
    secs.append(plan.credits_s)
    picture = work / 'picture.mp4'
    _xfade_chain(parts, secs, fade, picture, fps)

    # 5. titles and beat overlays on top of the cut
    vf = []
    ta, tb = plan.title_start_s, plan.title_start_s + 3.8
    if plan.show_title:
        tf = _textfile(work, 'series.txt', plan.series.upper())
        vf.append(f"drawtext=fontfile={FONT_BOLD}:textfile='{tf}':x=(w-tw)/2:y=h/2-90:fontsize=88:fontcolor=white:"
                  f"shadowcolor=black@0.6:shadowx=3:shadowy=3:enable='between(t,{ta:.2f},{tb:.2f})':"
                  f"alpha='min(1,(t-{ta:.2f})/0.6)*min(1,({tb:.2f}-t)/0.6)'")
        if plan.subtitle:
            tf = _textfile(work, 'subtitle.txt', plan.subtitle)
            vf.append(f"drawtext=fontfile={FONT}:textfile='{tf}':x=(w-tw)/2:y=h/2+20:fontsize=42:fontcolor=white:"
                      f"shadowcolor=black@0.6:shadowx=2:shadowy=2:enable='between(t,{ta + 0.5:.2f},{tb:.2f})':"
                      f"alpha='min(1,(t-{ta + 0.5:.2f})/0.6)*min(1,({tb:.2f}-t)/0.6)'")
    t = 0.0
    beat_windows = []
    for i, beat in enumerate(plan.beats):
        span = sum(s['seconds'] for s in shots if s['beat'] == i)
        beat_windows.append((t, t + span))
        if beat.overlay:
            tf = _textfile(work, f'overlay_{i}.txt', beat.overlay)
            vf.append(f"drawtext=fontfile={FONT}:textfile='{tf}':x=w-tw-56:y=48:fontsize=38:fontcolor=white:"
                      f"box=1:boxcolor=black@0.5:boxborderw=10:enable='between(t,{t + 0.3:.2f},{t + span - 0.3:.2f})'")
        t += span
    vf = vf or ['null']
    titled = work / 'titled.mp4'
    _run(['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error', '-i', str(picture), '-vf', ','.join(vf),
          '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '17', str(titled)])

    # 6. sound: narration + (optional) verified natural ambience, low under the voice
    mixed = work / 'mix.wav'
    amb_report = None
    if ambience_file:
        amb = work / 'ambience.wav'
        _run(['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error', '-stream_loop', '-1', '-i', str(ambience_file),
              '-t', f'{total:.3f}', '-ac', '2', '-ar', '48000',
              '-af', f'loudnorm=I=-34:TP=-6:LRA=11,afade=t=in:d=1.5,afade=t=out:st={total - 2:.3f}:d=2', str(amb)])
        _run(['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error', '-i', str(voice), '-i', str(amb),
              '-filter_complex', '[0:a]aformat=channel_layouts=stereo[v];[v][1:a]amix=inputs=2:normalize=0[m]',
              '-map', '[m]', '-ar', '48000', str(mixed)])
        amb_report = {'target_lufs': -34, 'voice_target_lufs': -16}
    else:
        _run(['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error', '-i', str(voice), '-ac', '2', str(mixed)])
    muxed = work / 'muxed.mp4'
    _run(['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error', '-i', str(titled), '-i', str(mixed),
          '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest', str(muxed)])
    burn_captions(muxed, ass, out)

    report = {'output_path': str(out), 'mode': 'footage', 'duration_s': round(_duration(out), 2),
              'planned_total_s': round(total, 2), 'resolution': f'{width}x{height}', 'fps': fps,
              'narration_backend': '+'.join(sorted(narrator.actual_backends)), 'voice_loudness': loud.model_dump(),
              'alignment': {'method': aligned.method, 'token_coverage': aligned.token_coverage, 'words': len(aligned.words)},
              'captions': count, 'caption_qc': caption_qc.model_dump(), 'srt_path': str(srt),
              'narration_starts_s': [round(s, 2) for s in tl['narration_starts']],
              'beat_windows_s': [[round(a, 2), round(b, 2)] for a, b in beat_windows],
              'shots': shot_report, 'clips': clip_info, 'ambience': {**(ambience or {}), **(amb_report or {})} or None,
              'credits': lines, 'license_gate': license_gate(plan, clip_info), 'ai_generated_shots': sum(1 for s in shot_report if s['ai_generated']),
              'ready_for_publication': False, 'manual_review_required': True}
    (work / 'render_report.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    return report


def main() -> None:
    import argparse
    import httpx
    from channel.footage import download_clip
    from scripts.footage_sheets import clip_info as commons_clip_info, has_audio
    ap = argparse.ArgumentParser(description='Render a footage-mode documentary sample (no upload)')
    ap.add_argument('--plan', type=Path, required=True)
    ap.add_argument('--voice-model', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    plan = load_plan(args.plan)
    files, infos, ambience, amb_file = {}, {}, None, None
    dl = args.out.parent / 'footage'
    with httpx.Client(trust_env=True) as client:
        for cid, src in plan.clips.items():
            if src.kind == 'pixabay':
                from channel import pixabay
                clip = pixabay.get_video(client, src.pixabay_id)  # key from the secret, never printed
                files[cid] = pixabay.download(client, clip['best']['url'], dl / f'{cid}.mp4')
                infos[cid] = {'source': 'pixabay', 'id': clip['id'], 'title': f"Pixabay #{clip['id']}",
                              'author': clip['author'], 'license': clip['license'], 'license_url': clip['license_url'],
                              'page': clip['page'], 'tags': clip['tags'], 'height': clip['best']['height'],
                              'has_audio': has_audio(files[cid]), 'location': src.location,
                              'species_verified': src.species_verified, 'ai_checked': src.ai_checked}
                continue
            if src.kind != 'commons':
                continue
            info = commons_clip_info(client, src.title)          # licence re-checked here
            ext = '.webm' if info['download'].endswith('.webm') else '.mp4'
            files[cid] = download_clip(client, info['download'], dl / f'{cid}{ext}')
            info['has_audio'] = has_audio(files[cid])
            info['location'] = src.location
            infos[cid] = info
        if plan.ambience:
            ambience = search_ambience(client, plan.ambience)
            if ambience:
                suffix = Path(urlparse(ambience['download']).path).suffix or '.ogg'
                amb_file = download_clip(client, ambience['download'], dl / f'ambience{suffix}')
    report = render_documentary(plan, args.voice_model, args.out, clip_files=files, clip_info=infos,
                                ambience=ambience, ambience_file=amb_file)
    print(json.dumps({k: report[k] for k in ('duration_s', 'captions', 'ai_generated_shots')} |
                     {'ambience': (report['ambience'] or {}).get('title')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
