"""Director: script -> validated Cinematic Production Spec, using free LLMs, constrained to the registry.

Stage 1 reads the story: entities, and every event (who does what to what, which state changes,
and the exact word that names it). Stage 2 plans shots over numbered narration words using only
registered techniques. The spec is then validated; blocking problems are sent back for repair (at
most `repairs` rounds). If it still fails, the Director returns the problems instead of a film.

    python -m studio.director script.txt --out studio/films/<id>/spec.json --id <id> [--lang en]
"""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable, Protocol

from pydantic import ValidationError

from .capabilities import catalog_for_director
from .spec import FilmSpec, SpecError, tokenize, validate

GRAMMAR = """You are the film director of a premium short-form video studio. Your films look like the best
editorial explainers on TikTok/Reels: every spoken idea is SHOWN, cut fast, with word-synced type.

Non-negotiable rules:
1. Every event the narration names (someone does something, something moves, appears, changes state)
   must be visible in the shot that covers that word. beat.at_word = index of the word that names it.
2. Shots cover the narration words contiguously and in order. Aim for 4-10 words per shot (about
   1.5-3.5 s); never exceed 14 words. Split long sentences into several shots.
3. Two worlds alternate: "story" = photoreal stills or clips of people, places and emotion (the human
   side, the problem, time and place); "explain" = a clean paper-white world with UI, data and type
   (the mechanism, the insight). Cut from one world to the other where the narration turns.
4. Interactions with software or devices (find, tap, type, submit, receive, open, read, call) use
   ui_flow with screens whose at_word / field at_word land on the words that name them.
5. Something travelling between two parties (a message, a file, money, an application) uses
   data_transfer with depart_word and arrive_word on the narrated words.
6. People, places and emotions use still_2_5d (or clip for real motion). Each still/clip needs an
   AssetRequest with a concrete photographic prompt: subject, action, setting, light, lens, mood. Never
   abstract ("success", "technology") and never text inside the image.
7. "title" only when one short phrase or quote IS the point; dots_subtract for "many vs one / remove";
   object_3d only with an existing asset.
8. Recurring characters and stateful objects are entities. Characters get a fixed appearance and seed.
   Stateful objects get initial_state; beats chain state_before -> state_after without skipping.
9. Transitions: cut by default; zoom_through to enter a device or detail; match when the same object
   continues into the next shot; dip_white for a jump in time; whip_blur for a fast change of topic.
10. Text: mode "words" at the top for most shots; 1-2 emphasis words per shot (the meaning-carrying
   words), mute filler words; "center_word" for a punchy beat; never cover the subject.
11. If something the narration needs cannot be shown with an available technique, list it in
   capability_gaps. Never substitute an unrelated picture. No real brands, logos or real people unless
   the user supplied them.
Return only JSON."""

STAGE1 = """Read this narration and return JSON:
{"entities": {"<id>": {"kind": "character|prop|location|ui|data|organization", "name": "...",
   "appearance": "<visual description, for characters: age, skin, hair, clothing>", "seed": <int or null>,
   "initial_state": "<for stateful objects or null>"}},
 "events": [{"word": <index of the word that names it>, "action": "...", "actor": "<entity id or null>",
   "object": "<entity id or null>", "state_before": null, "state_after": null, "visual": "<what we see>"}],
 "turns": [<word indices where the story turns from problem to mechanism to outcome>]}
Narration words (index:word):
"""

STAGE2 = """Plan the film as a FilmSpec JSON object matching this JSON schema:
{schema}

Available techniques (only those with available=true may be used; params must match params_schema):
{catalog}

Story analysis from stage 1:
{analysis}

Film id: {film_id}. Title: {title}. Format: {width}x{height} at 30 fps. Language: {lang}.
Narration text (put it verbatim in narration.text): {text}
Narration words (index:word):
{words}
"""

REPAIR = """Your FilmSpec has blocking problems. Return the corrected full FilmSpec JSON only.
Problems:
{problems}

Your previous JSON:
{previous}"""


class LLM(Protocol):
    def __call__(self, system: str, user: str) -> str: ...


def _json(text: str) -> dict:
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fence:
        text = fence.group(1)
    start = text.find("{")
    return json.loads(text[start:text.rfind("}") + 1])


class DirectorFailed(RuntimeError):
    def __init__(self, problems: list[str], last: dict | None):
        super().__init__("; ".join(problems[:8]))
        self.problems, self.last = problems, last


def direct(text: str, *, llm: LLM, film_id: str, title: str = "", language: str = "en",
           width: int = 1080, height: int = 1920, repairs: int = 2, log: Callable[[str], None] = print) -> FilmSpec:
    words = tokenize(text)
    numbered = " ".join(f"{i}:{w}" for i, w in enumerate(words))
    analysis = _json(llm(GRAMMAR, STAGE1 + numbered))
    log(f"stage 1: {len(analysis.get('entities', {}))} entities, {len(analysis.get('events', []))} events")
    schema = json.dumps(FilmSpec.model_json_schema(), separators=(",", ":"))
    catalog = json.dumps(catalog_for_director(), separators=(",", ":"))
    user = STAGE2.format(schema=schema, catalog=catalog, analysis=json.dumps(analysis), film_id=film_id,
                         title=title or film_id, width=width, height=height, lang=language, text=text, words=numbered)
    raw = _json(llm(GRAMMAR, user))
    for attempt in range(repairs + 1):
        raw["id"], raw.setdefault("title", title or film_id)
        raw.setdefault("narration", {})["text"] = text
        raw["narration"]["language"] = language
        raw["format"] = {"width": width, "height": height, "fps": 30}
        try:
            spec = FilmSpec(**raw)
            warnings = validate(spec)
            missed = _unshown_events(analysis, spec)
            if missed:
                raise SpecError(missed)
            for w in warnings:
                log("warning: " + w)
            log(f"spec valid after {attempt} repair(s): {len(spec.shots)} shots")
            return spec
        except ValidationError as e:
            problems = [f"{'.'.join(map(str, err['loc']))}: {err['msg']}" for err in e.errors()[:20]]
        except SpecError as e:
            problems = e.problems
        log(f"attempt {attempt}: {len(problems)} problem(s)")
        if attempt == repairs:
            raise DirectorFailed(problems, raw)
        raw = _json(llm(GRAMMAR, REPAIR.format(problems="\n".join(f"- {p}" for p in problems), previous=json.dumps(raw))))
    raise AssertionError("unreachable")


def _unshown_events(analysis: dict, spec: FilmSpec) -> list[str]:
    """Every event found in stage 1 must have a beat within 2 words of where it is narrated."""
    beats = [b.at_word for s in spec.shots for b in s.beats]
    out = []
    for ev in analysis.get("events", []):
        w = ev.get("word")
        if isinstance(w, int) and not any(abs(w - b) <= 2 for b in beats):
            out.append(f"event '{ev.get('action')}' at word {w} has no visible beat in any shot")
    return out


# ---------------------------------------------------------------- free providers (no SDKs)

PROVIDERS = [  # (env key, OpenAI-compatible base URL, free model)
    ("GEMINI_API_KEY", "https://generativelanguage.googleapis.com/v1beta/openai", "gemini-2.5-flash"),
    ("GROQ_API_KEY", "https://api.groq.com/openai/v1", "llama-3.3-70b-versatile"),
    ("OPENROUTER_API_KEY", "https://openrouter.ai/api/v1", "meta-llama/llama-3.3-70b-instruct:free"),
]


def free_llm(timeout: float = 240) -> LLM:
    available = [(k, u, m) for k, u, m in PROVIDERS if os.environ.get(k)]
    if not available:
        raise RuntimeError("no free LLM key in env (GEMINI_API_KEY / GROQ_API_KEY / OPENROUTER_API_KEY)")

    def call(system: str, user: str) -> str:
        errors = []
        for key, base, model in available:
            body = json.dumps({"model": model, "temperature": 0.4, "response_format": {"type": "json_object"},
                               "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}).encode()
            req = urllib.request.Request(base + "/chat/completions", data=body, method="POST",
                                         headers={"Authorization": f"Bearer {os.environ[key]}", "Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    return json.loads(r.read())["choices"][0]["message"]["content"]
            except (urllib.error.URLError, KeyError, json.JSONDecodeError, TimeoutError) as e:
                errors.append(f"{key.split('_')[0].lower()}: {getattr(e, 'code', '')} {type(e).__name__}")
        raise RuntimeError("all free providers failed: " + "; ".join(errors))

    return call


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("script", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--id", required=True)
    ap.add_argument("--title", default="")
    ap.add_argument("--lang", default="en")
    a = ap.parse_args()
    try:
        spec = direct(a.script.read_text().strip(), llm=free_llm(), film_id=a.id, title=a.title, language=a.lang)
    except DirectorFailed as e:
        a.out.with_suffix(".failed.json").write_text(json.dumps({"problems": e.problems, "last": e.last}, indent=1))
        raise SystemExit("director blocked:\n" + "\n".join(e.problems))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(spec.model_dump_json(indent=1, exclude_none=True) + "\n")
    print(a.out)
