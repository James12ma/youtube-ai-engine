"""YouTube chapter building, validation and formatting for every rendered video.

The validation rules are adapted from ``skills/yt-chapters/chapters.py`` in
Jakeschincariol/youtube-agent-skill (commit a2feb2104981a375ffd4f87ee04f4f5344ac43c6),
MIT License, Copyright (c) 2026 Jake Schincariol. See THIRD_PARTY_NOTICES.md.

LogicScript does NOT use that project's pause/vocabulary boundary detection: our
chapter boundaries come from the real narration timeline (Piper segment durations
or WhisperX-aligned chapter timings), which is more accurate.

YouTube silently ignores a chapter list unless all of these hold:
  * the first chapter starts at 00:00
  * there are at least three chapters
  * every chapter is at least 10 seconds long
LogicScript additionally requires strictly increasing, non-empty titles.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from pydantic import BaseModel, Field

MIN_CHAPTERS = 3
MIN_CHAPTER_SECONDS = 10.0
MAX_TITLE_CHARS = 100


class Chapter(BaseModel):
    start_s: float = Field(ge=0)
    title: str


class ChapterValidation(BaseModel):
    passed: bool
    errors: list[str] = Field(default_factory=list)
    chapter_count: int


def _clean_title(title: str) -> str:
    return " ".join(str(title).split())


def format_timestamp(seconds: float) -> str:
    total = int(seconds)  # YouTube links chapters at whole seconds; floor keeps 00:00 exact
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def validate_chapters(chapters: Sequence[Chapter], *, video_duration_s: float | None = None) -> ChapterValidation:
    errors: list[str] = []
    if len(chapters) < MIN_CHAPTERS:
        errors.append(f"need at least {MIN_CHAPTERS} chapters, got {len(chapters)}")
    if chapters and int(chapters[0].start_s) != 0:
        errors.append("first chapter must start at 00:00")
    for i, ch in enumerate(chapters):
        if not _clean_title(ch.title):
            errors.append(f"chapter {i + 1} has an empty title")
        elif len(_clean_title(ch.title)) > MAX_TITLE_CHARS:
            errors.append(f"chapter {i + 1} title exceeds {MAX_TITLE_CHARS} characters")
        if i and int(ch.start_s) <= int(chapters[i - 1].start_s):
            errors.append(f"chapter {i + 1} does not start after chapter {i}")
    starts = [int(c.start_s) for c in chapters]
    for i in range(len(starts) - 1):
        length = starts[i + 1] - starts[i]
        if length < MIN_CHAPTER_SECONDS:
            errors.append(f"chapter {i + 1} is {length}s long; minimum is {int(MIN_CHAPTER_SECONDS)}s")
    if chapters and video_duration_s is not None:
        last = video_duration_s - starts[-1]
        if last < MIN_CHAPTER_SECONDS:
            errors.append(f"last chapter is {last:.1f}s long; minimum is {int(MIN_CHAPTER_SECONDS)}s")
    return ChapterValidation(passed=not errors, errors=errors, chapter_count=len(chapters))


def normalize_timeline(timeline: Iterable[Mapping], *, video_duration_s: float | None = None) -> list[Chapter]:
    """Turn a narration timeline into a chapter list YouTube will accept where possible.

    ``timeline`` items need ``title`` and ``start`` (or ``start_s``); ``end``/``end_s`` is optional.
    Segments shorter than 10 s are merged into the previous chapter (or, for a short
    opening, the opening keeps 00:00 and takes the next segment's title). The result
    is still passed through :func:`validate_chapters` by callers, because a video that
    is simply too short cannot be fixed by merging.
    """
    items = []
    for raw in timeline:
        start = raw.get("start_s", raw.get("start"))
        if start is None:
            raise ValueError("timeline entries need a start time")
        end = raw.get("end_s", raw.get("end"))
        items.append({"title": _clean_title(raw.get("title", "")), "start": float(start),
                      "end": float(end) if end is not None else None})
    items.sort(key=lambda x: x["start"])
    if not items:
        return []
    items[0]["start"] = 0.0
    for i, item in enumerate(items):
        if item["end"] is None:
            item["end"] = items[i + 1]["start"] if i + 1 < len(items) else video_duration_s

    merged: list[dict] = []
    for item in items:
        if merged and int(item["start"]) - int(merged[-1]["start"]) < MIN_CHAPTER_SECONDS:
            # Previous chapter too short: absorb this one into it. A short 00:00 opening
            # takes the substantive title of what follows.
            prev = merged[-1]
            if prev["start"] == 0.0 and len(merged) == 1:
                prev["title"] = item["title"] or prev["title"]
            prev["end"] = item["end"]
            continue
        merged.append(dict(item))
    # A short final chapter is folded into the one before it.
    if len(merged) > 1 and merged[-1]["end"] is not None and merged[-1]["end"] - int(merged[-1]["start"]) < MIN_CHAPTER_SECONDS:
        tail = merged.pop()
        merged[-1]["end"] = tail["end"]
    return [Chapter(start_s=m["start"], title=m["title"]) for m in merged]


def timeline_from_segments(hook_title: str, section_headings: Sequence[str],
                           segment_durations: Sequence[float], *, closing_title: str | None = None) -> list[dict]:
    """Timeline for the channel renderer: segments are hook, each section, then CTA.

    The CTA is folded into the final section unless ``closing_title`` is given.
    """
    if len(segment_durations) != len(section_headings) + 2:
        raise ValueError("segment durations must be hook + sections + cta")
    timeline, offset = [], 0.0
    titles = [hook_title, *section_headings]
    for title, duration in zip(titles, segment_durations[:-1]):
        timeline.append({"title": title, "start": offset, "end": offset + float(duration)})
        offset += float(duration)
    cta = float(segment_durations[-1])
    if closing_title:
        timeline.append({"title": closing_title, "start": offset, "end": offset + cta})
    else:
        timeline[-1]["end"] += cta
    return timeline


def format_chapters(chapters: Sequence[Chapter]) -> str:
    return "\n".join(f"{format_timestamp(c.start_s)} {_clean_title(c.title)}" for c in chapters)


def load_timeline(path: Path) -> list[dict]:
    """Read a chapter timeline from a JSON list or from a render/QC report with a ``chapters`` key."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("chapters")
    if not isinstance(data, list):
        raise ValueError("chapter file must be a list or contain a 'chapters' list")
    return data
