"""Title and thumbnail-text checks applied to every release package.

Adapted from ``skills/yt-package/title.py`` in Jakeschincariol/youtube-agent-skill
(commit a2feb2104981a375ffd4f87ee04f4f5344ac43c6), MIT License,
Copyright (c) 2026 Jake Schincariol. See THIRD_PARTY_NOTICES.md.

Every finding carries a ``source``:

* ``youtube``  - a real platform limit (title empty or over 100 characters, or
  containing ``<``/``>``, which the YouTube Data API rejects). Always blocking.
* ``project_policy`` - a LogicScript quality preference (60-character desktop
  title, thumbnail word count, title/thumbnail word repetition). These are NOT
  YouTube requirements. Their thresholds and whether they block are configured by
  :class:`QualityPolicy`; by default they are advisory warnings.
* ``style`` - editorial hints that can never block.

LogicScript changes from the original: blocking/advisory split, configurable
policy, plural-insensitive duplicate matching, and the "add a number" hint
reworded because numbers in titles must come from verified claims.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

YOUTUBE_TITLE_MAX = 100  # YouTube Data API hard limit
FORBIDDEN_CHARS = re.compile(r'[<>]')  # rejected by the YouTube Data API in titles/descriptions

VAGUE = {"amazing", "incredible", "insane", "crazy", "huge", "massive", "ultimate", "best",
         "powerful", "secret", "revolutionary", "mindblowing", "epic", "perfect", "complete",
         "everything"}
STOP = {"the", "a", "an", "of", "for", "to", "in", "on", "and", "or", "is", "are", "with",
        "your", "you", "my", "i", "this", "that", "it", "how", "what", "why"}

Severity = Literal["block", "warn", "off"]


class QualityPolicy(BaseModel):
    """LogicScript packaging policy. Defaults warn; set a rule to "block" to enforce it."""
    model_config = ConfigDict(extra='forbid')

    title_desktop_chars: int = Field(default=60, ge=10, le=YOUTUBE_TITLE_MAX)
    title_desktop_rule: Severity = "warn"
    title_mobile_chars: int = Field(default=40, ge=10, le=YOUTUBE_TITLE_MAX)
    thumbnail_max_words: int = Field(default=3, ge=1, le=20)
    thumbnail_word_rule: Severity = "warn"
    thumbnail_duplicate_rule: Severity = "warn"
    thumbnail_text_required: Severity = "warn"
    # Chapters the owner supplied but YouTube would ignore are a defect we would write
    # into the description ourselves, so this one blocks by default.
    invalid_chapters_rule: Literal["block", "warn"] = "block"

    @classmethod
    def load(cls, path: Path | None) -> "QualityPolicy":
        if path is None:
            return cls()
        return cls.model_validate(json.loads(Path(path).read_text(encoding='utf-8')))


class PackagingFinding(BaseModel):
    code: str
    message: str
    source: Literal["youtube", "project_policy", "style"]


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


def mobile_preview(title: str, limit: int = 40) -> str:
    title = " ".join(title.split())
    if len(title) <= limit:
        return title
    return title[:limit].rsplit(" ", 1)[0] + "..."


def thumbnail_findings(title: str, thumbnail_text: str, policy: QualityPolicy) -> list[tuple[Severity, PackagingFinding]]:
    out: list[tuple[Severity, PackagingFinding]] = []
    n_words = len(_words(thumbnail_text))
    if n_words > policy.thumbnail_max_words:
        out.append((policy.thumbnail_word_rule, PackagingFinding(
            code="thumbnail-length", source="project_policy",
            message=f"{n_words} words on the thumbnail; project policy is {policy.thumbnail_max_words} "
                    "or fewer for legibility at feed size")))
    shared = _content_words(title) & _content_words(thumbnail_text)
    if shared:
        out.append((policy.thumbnail_duplicate_rule, PackagingFinding(
            code="duplicate", source="project_policy",
            message="thumbnail repeats the title on: " + ", ".join(sorted(shared))
                    + "; project policy prefers the thumbnail to add what the title does not")))
    return out


def lint_packaging(title: str, thumbnail_text: str | None = None,
                   policy: QualityPolicy | None = None) -> PackagingReport:
    policy = policy or QualityPolicy()
    t = " ".join(title.split())
    n = len(t)
    blocking: list[PackagingFinding] = []
    advisories: list[PackagingFinding] = []

    def route(severity: Severity, finding: PackagingFinding):
        if severity == "block":
            blocking.append(finding)
        elif severity == "warn":
            advisories.append(finding)

    # Real YouTube limits: always blocking.
    if not t:
        blocking.append(PackagingFinding(code="empty", source="youtube", message="title is empty"))
    elif n > YOUTUBE_TITLE_MAX:
        blocking.append(PackagingFinding(code="youtube-length", source="youtube",
                                         message=f"{n} characters; YouTube's limit is {YOUTUBE_TITLE_MAX}"))
    if FORBIDDEN_CHARS.search(t):
        blocking.append(PackagingFinding(code="forbidden-chars", source="youtube",
                                         message="title contains < or >, which YouTube rejects"))

    # Project policies: configurable.
    if policy.title_desktop_chars < n <= YOUTUBE_TITLE_MAX:
        route(policy.title_desktop_rule, PackagingFinding(
            code="length", source="project_policy",
            message=f"{n} characters; desktop search usually truncates near {policy.title_desktop_chars} "
                    "(project policy, not a YouTube requirement)"))
    if n > policy.title_mobile_chars:
        advisories.append(PackagingFinding(
            code="mobile", source="style",
            message=f'mobile feed shows about "{mobile_preview(t, policy.title_mobile_chars)}"; '
                    "check the subject survives"))

    # Style hints: never block.
    caps = [w for w in t.split() if len(w) > 2 and w.isupper()]
    if len(caps) > 2:
        advisories.append(PackagingFinding(code="shouting", source="style",
                          message=f"{len(caps)} all-caps words; two is a common ceiling before it reads as spam"))
    vague = sorted({w for w in _words(t) if w in VAGUE})
    if vague:
        advisories.append(PackagingFinding(code="vague", source="style",
                          message=", ".join(vague) + "; replace with a concrete name, tool or step"))
    if t and not re.search(r"\d", t):
        advisories.append(PackagingFinding(code="no-anchor", source="style",
                          message="no concrete date or number; a specific anchor often helps "
                                  "(numbers must come from verified claims)"))
    if t and not [w for w in _words(t)[:3] if w not in STOP]:
        advisories.append(PackagingFinding(code="front-load", source="style",
                          message="the first three words are all filler; move the subject forward"))

    thumb = None
    if thumbnail_text is not None and thumbnail_text.strip():
        thumb = " ".join(thumbnail_text.split())
        for severity, finding in thumbnail_findings(t, thumb, policy):
            route(severity, finding)
    else:
        route(policy.thumbnail_text_required, PackagingFinding(
            code="thumbnail-text", source="project_policy",
            message="thumbnail text unknown; pass it so the title/thumbnail pairing can be reviewed"))

    return PackagingReport(title=t, title_chars=n, thumbnail_text=thumb,
                           mobile_preview=mobile_preview(t, policy.title_mobile_chars),
                           blocking=blocking, advisories=advisories)
