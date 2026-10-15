"""Title and thumbnail-text checks applied to every release package.

Adapted from ``skills/yt-package/title.py`` in Jakeschincariol/youtube-agent-skill
(commit a2feb2104981a375ffd4f87ee04f4f5344ac43c6), MIT License,
Copyright (c) 2026 Jake Schincariol. See THIRD_PARTY_NOTICES.md.

Two outcome classes are kept strictly separate:

* ``blocking`` - objective defects that stop packaging: the title is cut off in
  desktop search (> 60 characters) or exceeds YouTube's 100-character limit,
  the thumbnail text repeats a title word, or the thumbnail carries more than
  three words.
* ``advisories`` - editorial suggestions that are recorded for the owner but
  never stop anything (mobile preview cut, all-caps, vague words, no concrete
  anchor, filler at the front).

LogicScript changes from the original: plural-insensitive duplicate matching,
three-word thumbnail ceiling (the original prose rule; its code allowed four),
and the "add a number" hint reworded because numbers in titles must be backed by
verified claims under LogicScript policy.
"""
from __future__ import annotations

import re

from pydantic import BaseModel, Field

DESKTOP_LIMIT = 60
MOBILE_LIMIT = 40
HARD_LIMIT = 100
MAX_THUMBNAIL_WORDS = 3
MAX_CAPS_WORDS = 2

VAGUE = {"amazing", "incredible", "insane", "crazy", "huge", "massive", "ultimate", "best",
         "powerful", "secret", "revolutionary", "mindblowing", "epic", "perfect", "complete",
         "everything"}
STOP = {"the", "a", "an", "of", "for", "to", "in", "on", "and", "or", "is", "are", "with",
        "your", "you", "my", "i", "this", "that", "it", "how", "what", "why"}


class PackagingFinding(BaseModel):
    code: str
    message: str


class PackagingReport(BaseModel):
    title: str
    title_chars: int
    thumbnail_text: str | None = None
    mobile_preview: str
    blocking: list[PackagingFinding] = Field(default_factory=list)
    advisories: list[PackagingFinding] = Field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.blocking

    def summary(self) -> dict:
        data = self.model_dump()
        data["passed"] = self.passed
        return data


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9']+", text.lower())


def _stem(word: str) -> str:
    """Very small plural folding so 'workflow' and 'workflows' count as the same word."""
    if len(word) > 4 and word.endswith("ies"):
        return word[:-3] + "y"
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def _content_words(text: str) -> set[str]:
    return {_stem(w) for w in _words(text) if w not in STOP}


def mobile_preview(title: str) -> str:
    title = " ".join(title.split())
    if len(title) <= MOBILE_LIMIT:
        return title
    head = title[:MOBILE_LIMIT].rsplit(" ", 1)[0]
    return head + "..."


def thumbnail_problems(title: str, thumbnail_text: str) -> list[PackagingFinding]:
    """Blocking problems of a title/thumbnail pairing (reused by make_thumbnail)."""
    problems = []
    n_words = len(_words(thumbnail_text))
    if n_words > MAX_THUMBNAIL_WORDS:
        problems.append(PackagingFinding(
            code="thumbnail-length",
            message=f"{n_words} words on the thumbnail; {MAX_THUMBNAIL_WORDS} is the ceiling at feed size"))
    shared = _content_words(title) & _content_words(thumbnail_text)
    if shared:
        problems.append(PackagingFinding(
            code="duplicate",
            message="thumbnail repeats the title on: " + ", ".join(sorted(shared))
                    + "; the thumbnail should say what the title does not"))
    return problems


def lint_packaging(title: str, thumbnail_text: str | None = None) -> PackagingReport:
    t = " ".join(title.split())
    n = len(t)
    blocking: list[PackagingFinding] = []
    advisories: list[PackagingFinding] = []

    if not t:
        blocking.append(PackagingFinding(code="empty", message="title is empty"))
    elif n > HARD_LIMIT:
        blocking.append(PackagingFinding(code="length", message=f"{n} characters; YouTube's hard limit is {HARD_LIMIT}"))
    elif n > DESKTOP_LIMIT:
        blocking.append(PackagingFinding(
            code="length", message=f"{n} characters; desktop search truncates near {DESKTOP_LIMIT}"))

    if n > MOBILE_LIMIT:
        advisories.append(PackagingFinding(
            code="mobile", message=f'mobile feed shows about "{mobile_preview(t)}"; check the subject survives'))

    caps = [w for w in t.split() if len(w) > 2 and w.isupper()]
    if len(caps) > MAX_CAPS_WORDS:
        advisories.append(PackagingFinding(
            code="shouting", message=f"{len(caps)} all-caps words; two is the ceiling before it reads as spam"))

    vague = sorted({w for w in _words(t) if w in VAGUE})
    if vague:
        advisories.append(PackagingFinding(
            code="vague", message=", ".join(vague) + "; replace with a concrete name, tool or step"))

    if t and not re.search(r"\d", t):
        advisories.append(PackagingFinding(
            code="no-anchor",
            message="no concrete name, date or number; a specific anchor usually helps "
                    "(numbers must come from verified claims)"))

    if t and not [w for w in _words(t)[:3] if w not in STOP]:
        advisories.append(PackagingFinding(
            code="front-load", message="the first three words are all filler; move the subject forward"))

    if thumbnail_text is not None:
        thumb = " ".join(thumbnail_text.split())
        if not thumb:
            blocking.append(PackagingFinding(code="thumbnail-empty", message="thumbnail text is empty"))
        else:
            blocking.extend(thumbnail_problems(t, thumb))
    else:
        thumb = None

    return PackagingReport(title=t, title_chars=n, thumbnail_text=thumb, mobile_preview=mobile_preview(t),
                           blocking=blocking, advisories=advisories)
