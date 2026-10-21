"""Checks a plan before anything expensive runs. Every problem is a sentence the Director can act on.

Rules
 - schema valid, style pack known, scenes known (or custom code present)
 - every phrase used for timing is really spoken in its beat
 - visual coverage: within each beat the gap between visual events (shot starts and cues) is at most
   the style's max_static_s, so every part of the narration has something happening on screen
 - custom code and built-in scenes render without JS errors, are not blank and change over time
"""
from __future__ import annotations

from pathlib import Path

from pydantic import ValidationError

from .audio import estimate
from .catalog import SCENES
from .plan import VideoPlan, spoken
from .resolve import PlanTimingError, resolve
from .styles import resolve as resolve_style


def check_plan(raw: dict | VideoPlan, *, render_check: bool = True, work: Path | None = None) -> tuple[VideoPlan | None, list[str]]:
    problems: list[str] = []
    try:
        plan = raw if isinstance(raw, VideoPlan) else VideoPlan.model_validate(raw)
    except ValidationError as e:
        return None, [f"{'.'.join(map(str, err['loc']))}: {err['msg']}" for err in e.errors()[:12]]
    try:
        style = resolve_style(plan.style)
    except ValueError as e:
        return plan, [str(e)]
    for bi, beat in enumerate(plan.beats):
        for si, shot in enumerate(beat.shots):
            if shot.scene != 'custom' and shot.scene not in SCENES:
                problems.append(f"beat {bi} shot {si}: unknown scene '{shot.scene}' (use a built-in scene or 'custom' with code)")
    if problems:
        return plan, problems
    narration = estimate([spoken(b.narration) for b in plan.beats])
    try:
        res = resolve(plan, narration)
    except PlanTimingError as e:
        return plan, [str(e)]
    limit = float(style.get('max_static_s', 2.8)) + 0.4   # estimate tolerance
    shots = res.data['shots']
    for bi, beat in enumerate(plan.beats):
        b0 = res.beat_starts[bi]; b1 = b0 + narration.beats[bi].duration
        events = sorted({b0} | {s['start'] for s in shots if s['id'].startswith(f'{bi}.')} |
                        {c['at'] for s in shots if s['id'].startswith(f'{bi}.') for c in s['cues']} | {b1})
        gap = max((b - a for a, b in zip(events, events[1:])), default=0)
        if gap > limit:
            problems.append(f'beat {bi} ("{spoken(beat.narration)[:60]}..."): {gap:.1f}s with nothing new on screen; '
                            f'add cues tied to phrases of this beat or split it into more shots (max {limit - .4:.1f}s)')
    if problems or not render_check:
        return plan, problems
    from .render import snapshot
    times = []
    for s in shots:
        d = s['end'] - s['start']
        times += [s['start'] + .05, s['start'] + d * .55, s['end'] - .05]
    rep = snapshot(res.data, times, work or Path('/tmp/studio_check'))
    for e in rep['js_errors'][:6]:
        problems.append('JavaScript error: ' + e)
    for i, s in enumerate(shots):
        if rep['shot_area'][i] < 0.01:
            problems.append(f"shot {s['id']} ({s['scene']}) draws nothing visible")
        ch = rep['changes'][i * 3:i * 3 + 2]
        if len(ch) == 2 and max(ch) < 0.4:
            problems.append(f"shot {s['id']} ({s['scene']}) does not change over time; animate it on its cues")
        if rep['shot_overflow'][i] > 0.06:
            problems.append(f"shot {s['id']} ({s['scene']}) draws {rep['shot_overflow'][i]:.0%} outside its box")
    return plan, problems
