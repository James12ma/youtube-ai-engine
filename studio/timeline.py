"""Bind a validated spec to real narration word times and emit the Editor's render plan (frames).

Cuts land just before the first word of each shot (a small lead keeps the picture ahead of the
voice, as in the reference), beats and SFX land on their words' frames, and the plan lists exactly
which assets the Editor needs. `estimate_word_times` exists only for layout previews; a final
render requires times from the actual voice track.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .spec import FilmSpec, validate

LEAD_S = 0.12  # picture changes slightly before the word, never after it


def estimate_word_times(text: str, words: list[str], wps: float = 2.7) -> list[tuple[float, float]]:
    """Rough speech timing for previews: per-word length by syllables, pauses at punctuation."""
    times, t = [], 0.25
    rest = text
    for w in words:
        i = rest.find(w)
        rest_after = rest[i + len(w):] if i >= 0 else rest
        syl = max(1, len(re.findall(r"[aeiouy]+", w.lower())))
        dur = 0.16 + 0.11 * syl
        times.append((round(t, 3), round(t + dur, 3)))
        t += dur + 0.04
        nxt = rest_after[:2]
        if any(p in nxt for p in ".?!"):
            t += 0.38
        elif any(p in nxt for p in ",:;"):
            t += 0.18
        rest = rest_after
    scale = (len(words) / wps) / t if t else 1
    return [(round(a * scale, 3), round(b * scale, 3)) for a, b in times]


def build_plan(spec: FilmSpec, *, assets: dict[str, str], preview: bool = False) -> dict:
    words = spec.tokens
    if spec.narration.word_times is None:
        if not preview:
            raise ValueError("final render needs word times from the real voice track")
        spec.narration.word_times = estimate_word_times(spec.narration.text, words)
    warnings = validate(spec, require_timing=True)
    fps = spec.format.fps
    wt = spec.narration.word_times
    f = lambda s: max(0, round(s * fps))  # noqa: E731
    word_frames = [{"i": i, "text": w, "from": f(a), "to": f(b)} for i, (w, (a, b)) in enumerate(zip(words, wt))]
    end_frame = f(wt[-1][1] + spec.tail_seconds)
    starts = [0] + [max(1, f(wt[s.words[0]][0] - LEAD_S)) for s in spec.shots[1:]]
    shots = []
    missing = []
    for k, s in enumerate(spec.shots):
        start, stop = starts[k], starts[k + 1] if k + 1 < len(spec.shots) else end_frame
        if stop - start < 6:
            raise ValueError(f"shot {s.id} would last {stop - start} frames; merge it with a neighbour")
        params = dict(s.params)
        for key in ("image", "video", "asset", "background_image"):
            ref = params.get(key)
            if ref:
                if ref not in assets:
                    missing.append(ref)
                params[key] = assets.get(ref, f"missing:{ref}")
        for scr in params.get("screens", []):  # word indices inside screens become frames
            for wk in ("at_word", "tap_cta_word", "arrive_word", "highlight_word"):
                if wk in scr:
                    scr[wk.replace("word", "frame")] = word_frames[scr[wk]]["from"]
            for fld in scr.get("fields", []):
                if "at_word" in fld:
                    fld["at_frame"] = word_frames[fld["at_word"]]["from"]
        for wk in ("depart_word", "arrive_word", "remove_word"):
            if wk in params:
                params[wk.replace("word", "frame")] = word_frames[params[wk]]["from"]
        shots.append({
            "id": s.id, "world": s.world, "technique": s.technique, "from": start, "to": stop,
            "params": params, "camera": s.camera.model_dump(), "transition": s.transition_in.model_dump(),
            "text": {**s.text.model_dump(), "words": [word_frames[i] for i in range(s.words[0], s.words[1] + 1)]},
            "beats": [{**b.model_dump(), "frame": word_frames[b.at_word]["from"]} for b in s.beats],
            "sfx": [{**c.model_dump(), "frame": word_frames[c.at_word]["from"]} for c in s.sfx],
        })
    return {
        "id": spec.id, "title": spec.title, "width": spec.format.width, "height": spec.format.height,
        "fps": fps, "durationInFrames": end_frame, "style": spec.style,
        "voice": assets.get(spec.narration.audio) if spec.narration.audio else None,
        "music": {**spec.music.model_dump(), "asset": assets.get(spec.music.asset) if spec.music.asset else None},
        "words": word_frames, "shots": shots, "preview_timing": preview and spec.narration.audio is None,
        "missing_assets": sorted(set(missing)), "warnings": warnings,
    }


def write_plan(spec_path: Path, out: Path, assets: dict[str, str], preview: bool = False) -> dict:
    spec = FilmSpec(**json.loads(spec_path.read_text()))
    plan = build_plan(spec, assets=assets, preview=preview)
    out.write_text(json.dumps(plan, indent=1))
    return plan
