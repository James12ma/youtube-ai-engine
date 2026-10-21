"""The Director: prompt -> script -> visual plan, using free LLMs, with automatic self-repair.

1. write_script: the narration, cut into beats (or the owner's exact script, never rewritten)
2. plan_visuals: for each beat, the shots and cues that SHOW what is said (batched, so long videos fit)
3. repair: the plan is validated (timing, visual coverage, real rendering of every shot); the problems
   are sent back to the model, which fixes only the failing beats. Up to `rounds` times.
Models: free tiers only (Groq, Gemini, OpenRouter ':free'), tried in order; no paid route exists here.
"""
from __future__ import annotations

import dataclasses
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Callable, Optional

from pydantic import BaseModel, Field

from .catalog import prompt_catalog
from .plan import Beat, Shot, VideoPlan, spoken
from .styles import PACKS
from .validate import check_plan

EXAMPLE = Path(__file__).with_name('examples') / 'job_application.json'


class Script(BaseModel):
    title: str = Field(max_length=100)
    style: str = Field(description='one of the style packs')
    music: str = Field(default='soft', description='soft | pulse | playful | none')
    beats: list[str] = Field(min_length=1, max_length=60, description='narration, one or two sentences each')


class BeatVisual(BaseModel):
    beat: int
    keywords: list[str] = Field(default_factory=list, max_length=3)
    shots: list[Shot] = Field(min_length=1, max_length=4)


class VisualBatch(BaseModel):
    beats: list[BeatVisual]


# ------------------------------------------------------------------ model access
CANDIDATES = [('groq', None), ('gemini', None), ('openrouter', 'google/gemma-4-31b-it:free'),
              ('openrouter', 'nvidia/nemotron-3-super-120b-a12b:free'), ('openrouter', None)]
Ask = Callable[[str, type[BaseModel]], BaseModel]


def free_model(prompt: str, schema: type[BaseModel], *, max_tokens: int = 4096, rounds: int = 3) -> BaseModel:
    from adapters import GeminiAdapter, GroqAdapter, OpenRouterAdapter
    from adapters.base import LLMRequest
    from adapters.config import GEMINI_CONFIG, GROQ_CONFIG, OPENROUTER_CONFIG
    kinds = {'gemini': (GeminiAdapter, GEMINI_CONFIG, 'GEMINI_API_KEY'), 'groq': (GroqAdapter, GROQ_CONFIG, 'GROQ_API_KEY'),
             'openrouter': (OpenRouterAdapter, OPENROUTER_CONFIG, 'OPENROUTER_API_KEY')}
    errors = []
    for r in range(rounds):
        for kind, model in CANDIDATES:
            cls, cfg, key = kinds[kind]
            if not os.environ.get(key):
                continue
            try:
                with cls(config=dataclasses.replace(cfg, request_timeout=240.0)) as ad:
                    resp = ad.complete(LLMRequest(messages=[{'role': 'user', 'content': prompt}], schema=schema,
                                                  model=model, temperature=0.4, max_tokens=max_tokens))
                got = resp.parsed if getattr(resp, 'parsed', None) else schema.model_validate_json(resp.text)
                print(f'[director] {schema.__name__} by {kind}:{model or "default"}', file=sys.stderr)
                return got
            except Exception as exc:  # noqa: BLE001 - try the next free model
                errors.append(f'{kind}:{model or "default"}: {type(exc).__name__}: {str(exc)[:200]}')
        time.sleep(30 * (r + 1))
    raise RuntimeError('no free model answered: ' + ' | '.join(errors[-6:]))


# ------------------------------------------------------------------ steps
def write_script(prompt: str, *, language: str, seconds: int, fmt: str, style: str, ask: Ask) -> Script:
    words = int(seconds * 2.5)
    packs = ', '.join(PACKS)
    text = f"""You write narration for a {seconds}-second {fmt} video. Language: {language}.
Request from the owner: {prompt}

Write about {words} words of spoken narration, cut into beats of one short sentence each (two at most).
Every beat must describe something CONCRETE that can be shown: who does what, with what, where, what happens next.
Open with a hook in the first beat; end with a question to the viewer or a clear takeaway.
Never invent statistics, quotes, prices or names of real people; if a number is not certain, describe without it.
style: pick the best of [{packs}]{' (owner asked for: ' + style + ')' if style != 'auto' else ''}.
music: soft, pulse, playful or none. Return JSON only."""
    return ask(text, Script)


def _plan_prompt(script: Script, fmt: str, beats: list[tuple[int, str]], context: str, problems: list[str]) -> str:
    example = json.loads(EXAMPLE.read_text())
    ex = {'beats': [{'beat': i, 'keywords': re.findall(r'\*([^*]+)\*', b['narration']), 'shots': b['shots']}
                    for i, b in enumerate(example['beats'][:4])]}
    lines = '\n'.join(f'  beat {i}: "{t}"' for i, t in beats)
    fix = ('\nYOUR PREVIOUS PLAN FOR THESE BEATS HAD PROBLEMS. Fix all of them:\n- ' + '\n- '.join(problems)) if problems else ''
    return f"""You are the director of a {fmt} explainer video titled "{script.title}" (style {script.style}).
Your job: for every beat of narration, choose shots that SHOW exactly what is being said, as it is said.
Every concrete detail (a person, an action, an object, a step, a result) gets its own visible action, timed with a cue
whose "phrase" is copied word for word from that beat. Nothing may stay still for more than ~2.5 seconds.

{prompt_catalog()}

RULES
- Each beat: 1-3 shots. First shot has no "starts_at"; later shots set "starts_at" to a phrase of the beat.
- Cue "phrase" must be words copied exactly from the beat's narration (empty phrase = when the shot starts).
- Keep the same person (same look letter) and the same objects across beats: continuity matters.
- Optional "headline" (1-2 short lines, uppercase style, accent = index of the coloured line) on key shots only.
- "keywords": 1-2 words of the beat to highlight in captions.
- Use "custom" with code only when no built-in scene fits; code must follow the custom-scene rules.
{context}
EXAMPLE (another video):
{json.dumps(ex)[:3500]}

BEATS TO PLAN:
{lines}
{fix}
Return JSON {{"beats":[{{"beat":index,"keywords":[...],"shots":[...]}}]}} for exactly these beat indexes."""


def plan_visuals(script: Script, *, fmt: str, ask: Ask, batch: int = 4, context: str = '') -> dict[int, BeatVisual]:
    out: dict[int, BeatVisual] = {}
    idx = list(enumerate(script.beats))
    for k in range(0, len(idx), batch):
        part = idx[k:k + batch]
        got = ask(_plan_prompt(script, fmt, part, context + _continuity(out), []), VisualBatch)
        for bv in got.beats:
            if any(bv.beat == i for i, _ in part):
                out[bv.beat] = bv
    return out


def _continuity(done: dict[int, BeatVisual]) -> str:
    looks = set()
    for bv in done.values():
        for s in bv.shots:
            for c in (s.params.get('cast') or []):
                if isinstance(c, dict) and c.get('look'):
                    looks.add(c['look'])
            if s.params.get('look'):
                looks.add(s.params['look'])
    return f'\nAlready used person looks (keep the same people consistent): {sorted(looks)}' if looks else ''


def assemble(script: Script, visuals: dict[int, BeatVisual], *, fmt: str, language: str, brand: str) -> dict:
    beats = []
    for i, text in enumerate(script.beats):
        bv = visuals.get(i)
        narration = text
        for kw in (bv.keywords if bv else [])[:2]:
            kw = kw.strip('* ')
            if kw and re.search(r'\b' + re.escape(kw) + r'\b', narration) and f'*{kw}*' not in narration:
                narration = re.sub(r'\b' + re.escape(kw) + r'\b', f'*{kw}*', narration, count=1)
        shots = [s.model_dump() for s in bv.shots] if bv else [{'scene': 'title', 'params': {'text': text[:40]}}]
        beats.append({'narration': narration, 'shots': shots})
    return {'title': script.title, 'format': fmt, 'style': script.style if script.style in PACKS else 'explainer-dark',
            'language': language, 'brand': brand, 'music': script.music, 'beats': beats}


def _beats_of(problems: list[str]) -> set[int]:
    out = set()
    for p in problems:
        for m in re.finditer(r'\b(?:beat|shot) (\d+)', p):
            out.add(int(m.group(1)))
    return out


def direct(prompt: str, *, fmt: str = 'vertical', language: str = 'en', seconds: int = 45, style: str = 'auto',
           brand: str = '', script: Optional[Script] = None, ask: Ask | None = None, rounds: int = 3,
           work: Path | None = None, render_check: bool = True, log: Callable[[str], None] = print) -> tuple[VideoPlan, dict]:
    """Returns a validated plan and a report of what the Director did (including every repair)."""
    ask = ask or free_model
    report: dict[str, Any] = {'prompt': prompt, 'rounds': []}
    if script is None:
        script = write_script(prompt, language=language, seconds=seconds, fmt=fmt, style=style, ask=ask)
    elif style != 'auto':
        script = script.model_copy(update={'style': style})
    report['script'] = script.model_dump()
    log(f'script: {len(script.beats)} beats, style {script.style}')
    visuals = plan_visuals(script, fmt=fmt, ask=ask)
    raw = assemble(script, visuals, fmt=fmt, language=language, brand=brand)
    for r in range(rounds + 1):
        plan, problems = check_plan(raw, render_check=render_check, work=work)
        report['rounds'].append({'round': r, 'problems': problems})
        log(f'validation round {r}: {len(problems)} problem(s)')
        if not problems:
            report['passed'] = True
            return plan, report
        if r == rounds:
            break
        bad = _beats_of(problems) or set(range(len(script.beats)))
        part = [(i, script.beats[i]) for i in sorted(bad) if i < len(script.beats)]
        mine = [p for p in problems if not _beats_of([p]) or _beats_of([p]) & bad]
        fixed = ask(_plan_prompt(script, fmt, part, _continuity(visuals), mine), VisualBatch)
        for bv in fixed.beats:
            if bv.beat in bad:
                visuals[bv.beat] = bv
        raw = assemble(script, visuals, fmt=fmt, language=language, brand=brand)
    report['passed'] = False
    raise DirectorFailed(report)


class DirectorFailed(RuntimeError):
    def __init__(self, report: dict):
        self.report = report
        last = report['rounds'][-1]['problems'] if report.get('rounds') else []
        super().__init__('plan still has problems after repairs: ' + '; '.join(last[:5]))
