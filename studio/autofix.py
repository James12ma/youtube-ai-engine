"""Deterministic repairs applied to a plan before it is checked, so the Director (an LLM) only has to fix
what really needs judgement. Every change is recorded in plain words.

  - a later shot without `starts_at` gets the word that falls at its share of the beat
  - a phrase that is not spoken word for word is replaced by the closest spoken words (or dropped)
  - a cue spoken outside its shot is moved to the nearest word inside the shot
  - a stretch with nothing new on screen gets 'punch' cues (camera emphasis) on words inside it
"""
from __future__ import annotations

import copy
import difflib

from .audio import estimate, tokens
from .plan import spoken
from .styles import resolve as resolve_style


def _first(toks: list[str], phrase: str) -> int | None:
    want = tokens(phrase)
    for i in range(len(toks) - len(want) + 1):
        if want and toks[i:i + len(want)] == want:
            return i
    return None


def _phrase_at(toks: list[str], i: int) -> str:
    """Shortest run of words starting at i whose first occurrence in the beat is i."""
    for n in range(1, 5):
        cand = ' '.join(toks[i:i + n])
        if _first(toks, cand) == i:
            return cand
    return ' '.join(toks[max(0, i - 1):i + 3])


def _closest(toks: list[str], phrase: str) -> int | None:
    want = tokens(phrase)
    if not want or not toks:
        return None
    n = min(len(want), len(toks)); best, at = 0.0, None
    for i in range(len(toks) - n + 1):
        r = difflib.SequenceMatcher(None, ' '.join(want), ' '.join(toks[i:i + n])).ratio()
        if r > best:
            best, at = r, i
    return at if best >= 0.6 else None


def autofix(raw: dict) -> tuple[dict, list[str]]:
    raw = copy.deepcopy(raw); notes: list[str] = []
    beats = raw.get('beats') or []
    try:
        limit = float(resolve_style(raw.get('style', 'explainer-dark')).get('max_static_s', 2.8))
    except Exception:  # noqa: BLE001 - style problems are reported by the validator
        limit = 2.8
    for bi, beat in enumerate(beats):
        shots = beat.get('shots') or []
        toks = tokens(spoken(beat.get('narration', '')))
        if not toks or not shots:
            continue
        # 1) shot starts
        starts = [0]
        for si, shot in enumerate(shots[1:], 1):
            i = _first(toks, shot.get('starts_at') or '') if shot.get('starts_at') else None
            if i is None and shot.get('starts_at'):
                i = _closest(toks, shot['starts_at'])
            if i is None:
                i = round(si * len(toks) / len(shots))
            i = max(i, starts[-1] + 2)
            if i >= len(toks) - 1:
                notes.append(f'beat {bi}: dropped shot {si} (no words left for it)')
                shots[si] = None; continue
            phrase = _phrase_at(toks, i)
            if tokens(shot.get('starts_at') or '') != tokens(phrase):
                notes.append(f"beat {bi} shot {si}: starts_at {shot.get('starts_at')!r} -> {phrase!r}")
                shot['starts_at'] = phrase
            starts.append(i)
        shots = [s for s in shots if s is not None]; beat['shots'] = shots
        bounds = starts + [len(toks)]
        # 2) cues: spoken, and inside their shot
        for si, shot in enumerate(shots):
            lo, hi = bounds[si], bounds[si + 1] - 1
            keep = []
            for c in shot.get('cues') or []:
                if not c.get('phrase'):
                    keep.append(c); continue
                i = _first(toks, c['phrase'])
                if i is None:
                    i = _closest(toks, c['phrase'])
                if i is None:
                    notes.append(f"beat {bi}: cue {c.get('name')} phrase {c['phrase']!r} is not spoken; fires at shot start")
                    c['phrase'] = ''; keep.append(c); continue
                j = min(max(i, lo), hi)
                ph = _phrase_at(toks, j) if j != i or tokens(c['phrase']) != toks[i:i + len(tokens(c['phrase']))] else c['phrase']
                if _first(toks, ph) != j:
                    ph = _phrase_at(toks, j)
                if ph != c['phrase']:
                    notes.append(f"beat {bi} shot {si}: cue {c.get('name')} {c['phrase']!r} -> {ph!r}")
                    c['phrase'] = ph
                keep.append(c)
            shot['cues'] = keep
        # 3) coverage: estimated word times, add 'punch' where nothing happens for too long
        words = estimate([spoken(beat['narration'])]).beats[0]
        flat = [w['start'] for w in words.words for _ in tokens(w['text'])]
        if len(flat) != len(toks):
            continue
        dur = words.duration
        for _ in range(6):
            ev = {0.0, dur}
            for si, shot in enumerate(shots):
                ev.add(flat[bounds[si]] if si else 0.0)
                for c in shot.get('cues') or []:
                    i = _first(toks, c['phrase']) if c.get('phrase') else bounds[si]
                    ev.add(flat[i] if i is not None and i < len(flat) else 0.0)
            ev = sorted(ev)
            gaps = [(b - a, a, b) for a, b in zip(ev, ev[1:]) if b - a > limit]
            if not gaps:
                break
            _, a, b = max(gaps)
            mid = (a + b) / 2
            j = min(range(len(flat)), key=lambda k: abs(flat[k] - mid))
            if not (a < flat[j] < b):
                break
            si = max(k for k in range(len(shots)) if bounds[k] <= j)
            ph = _phrase_at(toks, j)
            shots[si].setdefault('cues', []).append({'name': 'punch', 'phrase': ph})
            notes.append(f"beat {bi}: added emphasis on {ph!r} ({b - a:.1f}s without change)")
    return raw, notes
