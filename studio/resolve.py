"""Turn a VideoPlan + narration timings into the frame-exact JSON the renderer draws.

Every shot and cue gets an absolute time taken from the narration: a shot starts when its
`starts_at` phrase is spoken, a cue fires when its `phrase` is spoken. A phrase that is not in its
beat's narration is an error (never guessed)."""
from __future__ import annotations

from dataclasses import dataclass

from .audio import Narration, tokens
from .plan import VideoPlan, keywords, spoken
from .styles import resolve as resolve_style

LEAD_S = 0.35          # silence before the first word
BEAT_GAP_S = 0.22      # pause between beats
TAIL_S = 0.9           # hold after the last word
STOP = set('a an the and or but of to in on for with is are was were be it this that you your i we our they their at as by from so then'.split())


class PlanTimingError(ValueError):
    pass


def phrase_time(words: list[dict], phrase: str, beat_i: int) -> float:
    want = tokens(phrase)
    if not want:
        raise PlanTimingError(f'beat {beat_i}: empty phrase')
    flat = [(tok, w['start']) for w in words for tok in tokens(w['text'])]
    for i in range(len(flat) - len(want) + 1):
        if [x[0] for x in flat[i:i + len(want)]] == want:
            return flat[i][1]
    raise PlanTimingError(f'beat {beat_i}: phrase {phrase!r} is not spoken in this beat')


def caption_chunks(words: list[dict], keys: set[str], max_words: int = 4, max_chars: int = 24) -> list[dict]:
    chunks, cur = [], []
    for w in words:
        if cur and (len(cur) >= max_words or len(' '.join(x['text'] for x in cur + [w])) > max_chars):
            chunks.append(cur); cur = []
        cur.append(w)
        if w['text'].rstrip()[-1:] in '.!?;:,' and len(cur) >= 2:
            chunks.append(cur); cur = []
    if cur:
        chunks.append(cur)
    out = []
    for ch in chunks:
        marked = [any(t in keys for t in tokens(w['text'])) for w in ch]
        if not any(marked):   # reference style: one highlighted word per caption
            cand = [(len(w['text'].strip('.,!?;:')), j) for j, w in enumerate(ch)
                    if len(w['text'].strip('.,!?;:')) >= 5 and tokens(w['text']) and tokens(w['text'])[0] not in STOP]
            if cand:
                marked[max(cand)[1]] = True
        out.append({'words': [{'text': w['text'], 'start': w['start'], 'key': k} for w, k in zip(ch, marked)],
                    'start': ch[0]['start'], 'end': ch[-1]['end']})
    return out


@dataclass
class Resolved:
    data: dict              # JSON for the browser runtime
    beat_starts: list[float]
    cues: list[dict]        # absolute cue list (for sound design / QA)
    shot_starts: list[float]


def resolve(plan: VideoPlan, narration: Narration, *, brand: str = '') -> Resolved:
    if len(narration.beats) != len(plan.beats):
        raise PlanTimingError('narration does not match the plan beats')
    style = resolve_style(plan.style)
    t, beat_starts, shots, all_cues, captions = LEAD_S, [], [], [], []
    for bi, (beat, audio) in enumerate(zip(plan.beats, narration.beats)):
        if spoken(beat.narration) != audio.text:
            raise PlanTimingError(f'beat {bi}: narration text changed after synthesis')
        beat_starts.append(t)
        words = [{'text': w['text'], 'start': w['start'] + t, 'end': w['end'] + t} for w in audio.words]
        local = audio.words
        for si, shot in enumerate(beat.shots):
            if si == 0:
                start = t if bi else 0.0
            else:
                if not shot.starts_at:
                    raise PlanTimingError(f'beat {bi} shot {si}: needs starts_at (a phrase of this beat)')
                start = t + phrase_time(local, shot.starts_at, bi)
            cues = []
            for c in shot.cues:
                at = start if not c.phrase else t + phrase_time(local, c.phrase, bi)
                cues.append({'name': c.name, 'at': round(at, 3), 'args': c.args})
            shots.append({'id': f'{bi}.{si}', 'scene': shot.scene, 'code': shot.code, 'params': shot.params,
                          'start': round(start, 3), 'cues': cues,
                          'headline': shot.headline.model_dump() if shot.headline else None,
                          'camera': shot.camera, 'transition': shot.transition, 'layout': shot.layout})
            all_cues += cues
        captions += caption_chunks(words, keywords(beat.narration))
        t += audio.duration + BEAT_GAP_S
    duration = round(t - BEAT_GAP_S + TAIL_S, 3)
    for i, s in enumerate(shots):
        s['end'] = shots[i + 1]['start'] if i + 1 < len(shots) else duration
        if s['end'] - s['start'] < 0.6:
            raise PlanTimingError(f"shot {s['id']} lasts {s['end'] - s['start']:.2f}s; shots need at least 0.6s")
        bad = [c['name'] for c in s['cues'] if not (s['start'] - 0.01 <= c['at'] <= s['end'])]
        if bad:
            raise PlanTimingError(f"shot {s['id']}: cues {bad} fall outside the shot")
    for i, c in enumerate(captions):   # captions stay up until the next one starts (no flicker)
        nxt = captions[i + 1]['start'] if i + 1 < len(captions) else duration - .2
        c['end'] = round(min(nxt, c['end'] + 1.2), 3)
    data = {'title': plan.title, 'format': plan.format, 'style': style, 'brand': brand or plan.brand,
            'duration': duration, 'fps': 30, 'shots': shots, 'captions': captions,
            'draft': narration.is_draft, 'narration': narration.backend}
    return Resolved(data, beat_starts, sorted(all_cues, key=lambda c: c['at']), [s['start'] for s in shots])
