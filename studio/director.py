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

from .capabilities import REGISTRY, catalog_for_director
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
4. A person using an app on a phone or laptop (find, tap, type, submit, receive, open, read, call)
   uses ui_flow with screens whose at_word / field at_word land on the words that name them, and every
   screen has its visible text filled in. Physical objects and machines (cards, chips, terminals,
   counters, keys, packages) are NOT phone apps: show them with still_2_5d close-ups (macro photo of
   the object doing the narrated thing) instead.
5. Something travelling between two parties (a message, a file, money, an application) uses
   data_transfer with depart_word and arrive_word on the narrated words.
6. People, places and emotions use still_2_5d (or clip for real motion). Each still/clip needs an
   AssetRequest with a concrete photographic prompt: subject, action, setting, light, lens, mood. Never
   abstract ("success", "technology") and never text inside the image.
7. "title" only when one short phrase or quote IS the point, and its kicker must be that concrete phrase
   or quote itself (e.g. the exact sentence a character wrote), never a label like "Statement"; dots_subtract for "many vs one / remove";
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

Worked example of two correct consecutive shots (structure only; never copy its content):
{example}

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


_GATE_A = Path(__file__).resolve().parent / "films" / "gate_a" / "spec.json"
EXAMPLE = json.dumps(json.loads(_GATE_A.read_text())["shots"][3:5], separators=(",", ":")) if _GATE_A.exists() else "{}"


class LLM(Protocol):
    def __call__(self, system: str, user: str) -> str: ...


def _compact(schema):
    """JSON schema without titles/descriptions/defaults: the field names already speak, and the free
    tiers cap prompts (Groq gpt-oss: 8000 tokens per minute)."""
    if isinstance(schema, dict):
        return {k: _compact(v) for k, v in schema.items() if k not in ("title", "description", "default", "examples")}
    if isinstance(schema, list):
        return [_compact(v) for v in schema]
    return schema


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
           width: int = 1080, height: int = 1920, repairs: int = 4, log: Callable[[str], None] = print) -> FilmSpec:
    words = tokenize(text)
    numbered = " ".join(f"{i}:{w}" for i, w in enumerate(words))
    analysis = _json(llm(GRAMMAR, STAGE1 + numbered))
    log(f"stage 1: {len(analysis.get('entities', {}))} entities, {len(analysis.get('events', []))} events")
    schema = json.dumps(_compact(FilmSpec.model_json_schema()), separators=(",", ":"))
    catalog = json.dumps([{k: (_compact(v) if k == "params_schema" else v) for k, v in c.items()}
                          for c in catalog_for_director() if c["available"]], separators=(",", ":"))
    gaps = [c["technique"] for c in catalog_for_director() if not c["available"]]
    catalog += f' (NOT available, report as capability_gaps if needed: {", ".join(gaps)})'
    user = STAGE2.format(schema=schema, catalog=catalog, analysis=json.dumps(analysis), film_id=film_id, example=EXAMPLE,
                         title=title or film_id, width=width, height=height, lang=language, text=text, words=numbered)
    raw = _json(llm(GRAMMAR, user))
    best: tuple[int, dict, list[str]] | None = None  # (problem count, raw, problems)
    for attempt in range(repairs + 1):
        raw["id"] = film_id
        raw.setdefault("title", title or film_id)
        raw.setdefault("narration", {})["text"] = text
        raw["narration"]["language"] = language
        raw["format"] = {"width": width, "height": height, "fps": 30}
        _drop_filler_emphasis(raw, words)
        _fit_worlds(raw)
        _keyed(raw, "entities")
        _keyed(raw, "assets")
        _inherit_entities(analysis, raw)
        merge_events(analysis, raw)
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
        log(f"attempt {attempt}: {len(problems)} problem(s): " + " | ".join(problems[:6]))
        # A plan without shots is a stub (e.g. a truncated answer): it ranks below any real plan.
        score = len(problems) + (0 if _has_shots(raw) else 10_000)
        if best is None or score < best[0]:
            best = (score, json.loads(json.dumps(raw)), problems)
        if attempt == repairs:
            raise DirectorFailed(best[2], best[1])
        if not _has_shots(best[1]):  # nothing worth repairing yet: plan again from the analysis
            raw = _json(llm(GRAMMAR, user))
            continue
        # Always repair the best version so far; a degenerate answer never replaces a good one.
        raw = _json(llm(GRAMMAR, REPAIR.format(problems="\n".join(f"- {p}" for p in best[2]), previous=json.dumps(best[1]))))
    raise AssertionError("unreachable")


def _keyed(raw: dict, field: str) -> None:
    """LLMs sometimes send a keyed map as a list of objects; key it by its id/name so the rest of the
    plan (shots referencing those keys) still validates. Anything else is left for validation to report."""
    v = raw.get(field)
    if isinstance(v, list) and all(isinstance(x, dict) and (x.get("id") or x.get("name")) for x in v):
        raw[field] = {str(x.get("id") or x.get("name")): {k: y for k, y in x.items() if k != "id"} for x in v}


FILLER = {"a", "an", "the", "to", "of", "in", "on", "at", "for", "and", "or", "but", "is", "are", "was", "it",
          "its", "her", "his", "their", "she", "he", "they", "this", "that", "with", "from", "by", "as", "be"}


def _drop_filler_emphasis(raw: dict, words: list[str]) -> None:
    """Emphasis is for meaning-carrying words; a big "TO" or "HER" reads as a mistake."""
    for shot in raw.get("shots") or []:
        t = shot.get("text") if isinstance(shot, dict) else None
        if isinstance(t, dict) and isinstance(t.get("emphasis"), list):
            t["emphasis"] = [i for i in t["emphasis"] if not (isinstance(i, int) and 0 <= i < len(words)
                             and words[i].lower().strip(".,!?;:'\"") in FILLER)]


def _fit_worlds(raw: dict) -> None:
    """A shot's world follows from its technique (a still close-up is always a photo); fix it here
    instead of spending a repair round on it."""
    for shot in raw.get("shots") or []:
        if isinstance(shot, dict) and shot.get("technique") in REGISTRY:
            worlds = REGISTRY[shot["technique"]].worlds
            if shot.get("world") not in worlds:
                shot["world"] = worlds[0]


def _has_shots(raw: dict) -> bool:
    return isinstance(raw.get("shots"), list) and any(isinstance(x, dict) for x in raw["shots"])


def _inherit_entities(analysis: dict, raw: dict) -> None:
    """Fields the planner left out of an entity (kind, name, appearance...) come from the stage-1
    analysis of the same entity; the name falls back to its key. Nothing is invented."""
    ents, known = raw.get("entities"), analysis.get("entities")
    if not isinstance(ents, dict):
        return
    for key, ent in ents.items():
        if not isinstance(ent, dict):
            continue
        for k, v in ((known or {}).get(key) or {}).items() if isinstance(known, dict) else ():
            if v is not None and ent.get(k) in (None, ""):
                ent[k] = v
        ent.setdefault("name", key.replace("_", " "))


def merge_events(analysis: dict, raw: dict) -> int:
    """Write stage-1 events the planner forgot into the shot that covers their word (no invention:
    action, actor, object and state change all come from the story analysis). Returns how many."""
    ents = raw.get("entities")
    entities = set(ents.keys()) if isinstance(ents, dict) else set()
    added = 0
    for ev in analysis.get("events", []):
        w = ev.get("word")
        if not isinstance(w, int):
            continue
        shots = raw.get("shots")
        for shot in shots if isinstance(shots, list) else []:
            rng = shot.get("words") if isinstance(shot, dict) else None
            if not (isinstance(rng, list) and len(rng) == 2 and all(isinstance(x, int) for x in rng)
                    and rng[0] <= w <= rng[1]):
                continue
            beats = shot.get("beats") or []
            if not any(isinstance(b, dict) and abs(b.get("at_word", -99) - w) <= 2 for b in beats):
                beats.append({"action": str(ev.get("action", "event"))[:80],
                              "actor": ev.get("actor") if ev.get("actor") in entities else None,
                              "object": ev.get("object") if ev.get("object") in entities else None,
                              "at_word": w, "note": str(ev.get("visual", ""))[:160]})
                added += 1
            shot["beats"] = beats
            break
    return added


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

PROVIDERS = [  # (env key, OpenAI-compatible base URL, free model), strongest first. Re-check names when a
    # provider answers 404 "no longer available" (the error body names the replacement).
    ("GEMINI_API_KEY", "https://generativelanguage.googleapis.com/v1beta/openai", "gemini-3.8-flash"),
    ("GEMINI_API_KEY", "https://generativelanguage.googleapis.com/v1beta/openai", "gemini-3.1-flash-lite"),
    ("GROQ_API_KEY", "https://api.groq.com/openai/v1", "openai/gpt-oss-120b"),
    # gpt-oss has an 8k tokens-per-minute free limit, smaller than one planning call; these allow more.
    ("GROQ_API_KEY", "https://api.groq.com/openai/v1", "meta-llama/llama-4-scout-17b-16e-instruct"),
    ("GROQ_API_KEY", "https://api.groq.com/openai/v1", "moonshotai/kimi-k2-instruct-0905"),
    ("GROQ_API_KEY", "https://api.groq.com/openai/v1", "llama-3.3-70b-versatile"),
    ("GROQ_API_KEY", "https://api.groq.com/openai/v1", "openai/gpt-oss-20b"),
    ("OPENROUTER_API_KEY", "https://openrouter.ai/api/v1", "google/gemma-4-26b-a4b-it:free"),
]
RETRYABLE = {429, 500, 502, 503, 504}


def free_llm(timeout: float = 240, rounds: int = 8, sleep=None) -> LLM:
    import time

    sleep = sleep or time.sleep
    available = [(k, u, m) for k, u, m in PROVIDERS if os.environ.get(k)]
    if not available:
        raise RuntimeError("no free LLM key in env (GEMINI_API_KEY / GROQ_API_KEY / OPENROUTER_API_KEY)")
    dead: set[str] = set()  # models that answered 404/400 (gone or unsupported) are skipped afterwards

    def call(system: str, user: str) -> str:
        errors = []
        for rnd in range(rounds):
            wait = 0.0
            for key, base, model in available:
                if model in dead:
                    continue
                body = json.dumps({"model": model, "temperature": 0.4, "response_format": {"type": "json_object"},
                                   "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}).encode()
                req = urllib.request.Request(base + "/chat/completions", data=body, method="POST", headers={
                    "Authorization": f"Bearer {os.environ[key]}", "Content-Type": "application/json",
                    "User-Agent": "youtube-ai-engine-studio/1.0"})
                try:
                    with urllib.request.urlopen(req, timeout=timeout) as r:
                        content = json.loads(r.read())["choices"][0]["message"]["content"]
                    print(f"[llm] {model} answered ({len(content)} chars)", flush=True)
                    return content
                except urllib.error.HTTPError as e:
                    detail = e.read()[:240].decode("utf-8", "replace").replace(os.environ[key], "***")
                    errors.append(f"r{rnd} {model}: HTTP {e.code} {detail}")
                    if e.code in RETRYABLE:
                        ra = e.headers.get("Retry-After") if e.headers else None
                        wait = max(wait, float(ra) if ra and ra.replace(".", "", 1).isdigit() else 20.0)
                    elif e.code in (400, 404):
                        dead.add(model)
                except (urllib.error.URLError, KeyError, json.JSONDecodeError, TimeoutError) as e:
                    errors.append(f"r{rnd} {model}: {type(e).__name__}")
                    wait = max(wait, 10.0)
            if rnd + 1 < rounds and wait:
                pause = min(max(wait, 20.0 * (rnd + 1)), 90)  # demand spikes last minutes, not seconds
                print(f"[llm] all busy; retrying in {pause:.0f}s", flush=True)
                sleep(pause)
        last = {}  # the latest error of every model, so no provider's reason is hidden
        for e in errors:
            last[e.split(":", 1)[0].split(" ", 1)[1]] = e
        raise RuntimeError("all free providers failed: " + " | ".join(last.values()))

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
