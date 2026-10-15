"""ADVISORY hook quality score. It never rejects, blocks or retries a script.

Adapted from ``skills/yt-script/hookscore.py`` and ``hooks.json`` in
Jakeschincariol/youtube-agent-skill (commit a2feb2104981a375ffd4f87ee04f4f5344ac43c6),
MIT License, Copyright (c) 2026 Jake Schincariol. See THIRD_PARTY_NOTICES.md.

Five keyword heuristics (specificity, address, stakes, curiosity, brevity) scored
0-100; the verdict is 60% of their mean plus 40% of the weakest one. The upstream
author reports it separates deliberately bad hooks from real ones, but barely
separates a creator's hits from their misses. Treat it as a prompt for review only.

LogicScript changes: the specificity fix no longer suggests adding a number,
because numeric hooks are rejected by the script gate unless cited.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel

FORMULA_FILE = Path(__file__).with_name("hook_formulas.json")

FILLER = {"basically", "actually", "literally", "just", "really", "very", "so", "kind", "sort", "like",
          "guys", "hey", "welcome", "today", "video", "subscribe", "channel"}
VAGUE = {"amazing", "incredible", "insane", "crazy", "huge", "massive", "game", "changer", "secret",
         "powerful", "ultimate", "best", "revolutionary", "mind", "blowing", "unbelievable"}
CONCRETE = re.compile(r"\b(\d[\d,.]*\s?(%|k|m|x|s|m|h)?|\$\d|\d+\s?(second|minute|hour|day|week|month|year)s?)\b", re.I)
YOU = re.compile(r"\b(you|your|you're|youre|yourself)\b", re.I)
STAKE = re.compile(r"\b(lose|lost|wasting|waste|quit|fail|broke|cost|risk|before|stop|never|die|dying|dead)\b", re.I)
CURIOSITY = re.compile(r"\b(why|how|what|which|until|before|but|nobody|almost|except|reason|actually)\b", re.I)

FIX = {
    "specificity": "replace a vague adjective with a concrete name, tool or step "
                   "(numbers need a cited claim under LogicScript policy)",
    "address": "say 'you' in the first six words",
    "stakes": "name what it costs the viewer to keep doing it the current way",
    "curiosity": "cut the half of the sentence that answers itself",
    "brevity": "aim for 9 to 24 words; read it out loud and stop where you run out of breath",
}


class HookScore(BaseModel):
    advisory: bool = True  # never a blocking gate
    hook: str
    properties: dict[str, int]
    verdict: int
    band: str
    formula: str
    formula_matches: int
    weakest: str
    suggestion: str


def _words(t: str) -> list[str]:
    return re.findall(r"[a-z0-9'%$.]+", t.lower())


def _clamp(v: float) -> int:
    return int(max(0, min(100, v)))


def _specificity(t: str) -> int:
    w = _words(t)
    if not w:
        return 0
    nums = len(CONCRETE.findall(t))
    vague = sum(1 for x in w if x in VAGUE)
    filler = sum(1 for x in w if x in FILLER)
    s = 34 + nums * 22 - vague * 16 - filler * 5
    s += min(18, 6 * sum(1 for x in t.split()[1:] if x[:1].isupper()))
    return _clamp(s)


def _address(t: str) -> int:
    first = 30 if YOU.search(" ".join(t.split()[:6])) else 0
    return _clamp(26 + len(YOU.findall(t)) * 20 + first)


def _stakes(t: str) -> int:
    return _clamp(22 + len(STAKE.findall(t)) * 26 + (14 if CONCRETE.search(t) else 0))


def _curiosity(t: str) -> int:
    q = 18 if t.strip().endswith("?") else 0
    closed = -18 if re.search(r"\b(because|so that|which means)\b", t, re.I) else 0
    return _clamp(24 + len(CURIOSITY.findall(t)) * 17 + q + closed)


def _brevity(t: str) -> int:
    n = len(_words(t))
    if n == 0:
        return 0
    if 9 <= n <= 24:
        return 100
    if n < 9:
        return max(30, 100 - (9 - n) * 11)
    return max(10, 100 - (n - 24) * 7)


PROPERTIES = (("specificity", _specificity), ("address", _address), ("stakes", _stakes),
              ("curiosity", _curiosity), ("brevity", _brevity))


@lru_cache(maxsize=1)
def load_formulas() -> list[dict]:
    return json.loads(FORMULA_FILE.read_text(encoding="utf-8"))["hooks"]


def classify(text: str) -> tuple[str, int]:
    best, hits = None, 0
    for formula in load_formulas():
        n = sum(1 for p in formula["match"] if re.search(p, text, re.I))
        if n > hits:
            best, hits = formula, n
    return (best["name"] if best else "Unclassified"), hits


def band(verdict: int) -> str:
    return "STRONG" if verdict >= 72 else "WORKABLE" if verdict >= 55 else "WEAK"


def score_hook(text: str) -> HookScore:
    hook = " ".join(str(text).split())
    parts = {name: fn(hook) for name, fn in PROPERTIES}
    vals = list(parts.values())
    verdict = round(0.6 * (sum(vals) / len(vals)) + 0.4 * min(vals))
    formula, hits = classify(hook)
    weakest = min(parts, key=parts.get)
    return HookScore(hook=hook, properties=parts, verdict=verdict, band=band(verdict), formula=formula,
                     formula_matches=hits, weakest=weakest, suggestion=FIX[weakest])


def write_hook_advisory(hook: str, path: Path) -> HookScore:
    """Persist the advisory next to a draft. Callers must never branch on the result."""
    result = score_hook(hook)
    Path(path).write_text(result.model_dump_json(indent=2), encoding="utf-8")
    return result
