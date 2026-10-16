"""Shared, lesson-agnostic narration stage for every lesson renderer.

``narrate_chapters`` runs real per-chapter TTS + forced alignment (Piper + WhisperX in
production). ``estimate_narration`` produces a clearly-labelled DRAFT timeline for offline
previews when no voice model is available; its timings are estimates, never presented
as alignment, and a draft can never pass the publication gates (method='estimated_draft').
"""
from __future__ import annotations

import re
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

from narration_pro.aligner import AlignmentResult, WordTimestamp, _tokens

DRAFT_WORDS_PER_SECOND = 2.55   # close to the measured One-Cent render: 1,189 words / 407 s ≈ 2.9 incl. pauses


@dataclass
class NarrationResult:
    words: list[WordTimestamp]
    timeline: list[dict]            # [{'title','start','end'}] in seconds, contiguous
    duration_s: float
    method: str                     # 'whisperx_ctc' | 'estimated_draft'
    audio_path: Path | None = None
    chapter_audio: list[Path] = field(default_factory=list)

    @property
    def is_draft(self) -> bool:
        return self.method != 'whisperx_ctc'


def concat_wavs(paths: Sequence[Path], out: Path) -> Path:
    with wave.open(str(out), 'wb') as dest:
        params = None
        for path in paths:
            with wave.open(str(path), 'rb') as src:
                if params is None:
                    params = src.getparams(); dest.setparams(params)
                elif src.getparams()[:3] != params[:3]:
                    raise ValueError('Inconsistent voice format')
                dest.writeframes(src.readframes(src.getnframes()))
    return Path(out)


def narrate_chapters(chapters: Sequence[dict], out: Path, *, narrator, aligner) -> NarrationResult:
    """Real narration: synthesize and force-align each chapter, then concatenate."""
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    words: list[WordTimestamp] = []; timeline = []; parts = []; offset = 0.0
    for i, chapter in enumerate(chapters):
        path = out / f'voice_{i:02}.wav'
        narrator.synthesize(chapter['narration'], path)
        aligned = aligner.align(path, chapter['narration'])
        for w in aligned.words:
            words.append(WordTimestamp(**{**w.model_dump(), 'start_s': w.start_s + offset, 'end_s': w.end_s + offset}))
        timeline.append({'title': chapter['title'], 'start': offset, 'end': offset + aligned.duration_s})
        offset += aligned.duration_s; parts.append(path)
    concat_wavs(parts, out / 'vo.wav')
    return NarrationResult(words=words, timeline=timeline, duration_s=offset, method='whisperx_ctc',
                           audio_path=out / 'vo.wav', chapter_audio=parts)


def estimate_narration(chapters: Sequence[dict], *, words_per_second: float = DRAFT_WORDS_PER_SECOND,
                       chapter_pause_s: float = 0.6) -> NarrationResult:
    """DRAFT timing only: evenly paced words with sentence pauses. Never used for publication."""
    words: list[WordTimestamp] = []; timeline = []; t = 0.0
    step = 1.0 / words_per_second
    for chapter in chapters:
        start = t
        for raw in chapter['narration'].split():
            dur = step * (1.0 + 0.04 * max(0, len(raw) - 6))
            words.append(WordTimestamp(word=raw, start_s=round(t, 3), end_s=round(t + dur * 0.92, 3)))
            t += dur
            if re.search(r'[.!?:]$', raw):
                t += 0.35
        t += chapter_pause_s
        timeline.append({'title': chapter['title'], 'start': start, 'end': t})
    return NarrationResult(words=words, timeline=timeline, duration_s=t, method='estimated_draft')


def cue_time(words: Sequence[WordTimestamp], phrase: str, start: float, end: float) -> float:
    """Time of the first aligned occurrence of ``phrase`` inside [start, end)."""
    flattened = []
    for w in words:
        if start - 0.05 <= w.start_s < end:
            flattened.extend((tok, w.start_s) for tok in _tokens(w.word))
    expected = _tokens(phrase)
    if not expected:
        raise ValueError('Empty cue phrase')
    for i in range(len(flattened) - len(expected) + 1):
        if [x[0] for x in flattened[i:i + len(expected)]] == expected:
            return flattened[i][1]
    raise ValueError('Cue not found in its chapter narration: ' + phrase)


def to_alignment(result: NarrationResult, transcript: str, audio_path: Path) -> AlignmentResult:
    return AlignmentResult(words=result.words, audio_path=str(audio_path), transcript=transcript, language='en',
                           alignment_model='whisperx per-chapter CTC' if not result.is_draft else 'DRAFT estimate',
                           duration_s=result.duration_s, token_coverage=1 if not result.is_draft else 0,
                           method=result.method)
