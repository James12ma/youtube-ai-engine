"""Read-only YouTube SEO intelligence for LogicScript and Alan7.

No SEOStudio scraping, publication, ranking promises or unauthorised paid API use.
Live lookup requires explicit --live and a separately configured API key.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx

API_ROOT = "https://www.googleapis.com/youtube/v3"
_VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
_CHANNEL_ID = re.compile(r"^UC[A-Za-z0-9_-]{22}$")
_LANG = re.compile(r"^[a-z]{2}(?:-[A-Za-z]{2,4})?$")
_REGION = re.compile(r"^[A-Z]{2}$")
_WORDS = re.compile(r"[^\W_]+", re.UNICODE)
_STOP = {"a", "an", "and", "the", "for", "with", "from", "how", "what", "your", "this",
         "that", "are", "you", "to", "of", "in", "is", "en", "los", "las", "para",
         "con", "que", "una", "por", "del", "como", "cómo", "de", "la", "el", "un"}


class SEOError(ValueError):
    """A safe error that never includes credentials."""


def video_id_from_url(value: str) -> str:
    """Only parse known YouTube hosts, not lookalikes or arbitrary domains."""
    value = value.strip()
    if _VIDEO_ID.fullmatch(value):
        return value
    parsed = urlparse(value)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https":
        raise SEOError("A HTTPS YouTube video URL is required")
    if host in {"youtube.com", "www.youtube.com", "m.youtube.com"}:
        if parsed.path == "/watch":
            result = parse_qs(parsed.query).get("v", [""])[0]
        elif parsed.path.startswith(("/shorts/", "/live/")):
            result = parsed.path.split("/")[2]
        else:
            result = ""
    elif host in {"youtu.be", "www.youtu.be"}:
        result = parsed.path.strip("/").split("/")[0]
    else:
        result = ""
    if not _VIDEO_ID.fullmatch(result):
        raise SEOError("Unrecognised YouTube video URL or ID")
    return result


def _get(client: httpx.Client, key: str, resource: str, **params: str | int) -> dict[str, Any]:
    if resource not in {"search", "videos", "channels"}:
        raise SEOError("Unsupported read-only endpoint")
    try:
        response = client.get(
            f"{API_ROOT}/{resource}",
            params={**params, "key": key},
            timeout=12,
            follow_redirects=False,
        )
        if response.status_code != 200:
            raise SEOError(f"YouTube API {resource} returned HTTP {response.status_code}")
        payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        if isinstance(exc, SEOError):
            raise
        raise SEOError(f"YouTube API {resource} unavailable or invalid response") from None
    if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
        raise SEOError("Unexpected YouTube API response")
    return payload


def collect_public_videos(
    *, api_key: str, query: str = "", video_url: str = "", channel_id: str = "",
    region: str = "US", language: str = "en", max_results: int = 8,
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    """Bounded read-only lookup: at most one search, one videos, one channels call.

    regionCode is video availability, NOT audience origin. Search results are NOT
    proof of keyword volume, competition, or algorithmic ranking advantage.
    """
    if not api_key.strip():
        raise SEOError("YOUTUBE_API_KEY is required for live public research")
    if not _REGION.fullmatch(region) or not _LANG.fullmatch(language):
        raise SEOError("Invalid region or language")
    if not 1 <= max_results <= 10:
        raise SEOError("max_results must be between 1 and 10")
    if sum(bool(x) for x in (query.strip(), video_url.strip(), channel_id.strip())) != 1:
        raise SEOError("Choose exactly one of query, video_url or channel_id")
    if len(query) > 120 or len(video_url) > 250:
        raise SEOError("Topic or video URL is too long")
    if channel_id and not _CHANNEL_ID.fullmatch(channel_id):
        raise SEOError("Invalid YouTube channel ID")
    own = client is None
    client = client or httpx.Client()
    try:
        ids: list[str] = []
        if query:
            response = _get(client, api_key, "search", part="id", type="video",
                            q=query.strip(), maxResults=max_results, regionCode=region,
                            relevanceLanguage=language, safeSearch="moderate")
            ids = [item.get("id", {}).get("videoId", "") for item in response["items"]]
            ids = [v for v in ids if _VIDEO_ID.fullmatch(v)]
        elif video_url:
            ids = [video_id_from_url(video_url)]
        else:
            response = _get(client, api_key, "search", part="id", type="video",
                            channelId=channel_id, maxResults=max_results,
                            order="date", safeSearch="moderate")
            ids = [item.get("id", {}).get("videoId", "") for item in response["items"]]
            ids = [v for v in ids if _VIDEO_ID.fullmatch(v)]
        ids = list(dict.fromkeys(ids))
        if not ids:
            return {"videos": [], "channels": [], "source": "youtube_data_api_v3"}
        response = _get(client, api_key, "videos", part="snippet,statistics,contentDetails",
                        id=",".join(ids), maxResults=max_results)
        mapping = {item.get("id"): item for item in response["items"]}
        videos = []
        for video_id in ids:
            entry = mapping.get(video_id)
            if not entry:
                continue
            snippet, statistics = entry.get("snippet", {}), entry.get("statistics", {})
            videos.append({
                "id": video_id,
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "title": snippet.get("title", ""),
                "description": snippet.get("description", "")[:500],
                "channel_id": snippet.get("channelId", ""),
                "channel_title": snippet.get("channelTitle", ""),
                "published_at": snippet.get("publishedAt", ""),
                "tags": snippet.get("tags", [])[:40],
                "view_count": _integer(statistics.get("viewCount")),
                "like_count": _integer(statistics.get("likeCount")),
                "comment_count": _integer(statistics.get("commentCount")),
                "duration": entry.get("contentDetails", {}).get("duration", ""),
            })
        channels_ids = list(dict.fromkeys(v["channel_id"] for v in videos if _CHANNEL_ID.fullmatch(v["channel_id"])))
        channels = []
        if channels_ids:
            response = _get(client, api_key, "channels", part="snippet,statistics",
                            id=",".join(channels_ids))
            for item in response["items"]:
                stats, snippet = item.get("statistics", {}), item.get("snippet", {})
                channels.append({
                    "id": item.get("id", ""),
                    "title": snippet.get("title", ""),
                    "subscriber_count": _integer(stats.get("subscriberCount")),
                    "hidden_subscriber_count": bool(stats.get("hiddenSubscriberCount")),
                    "video_count": _integer(stats.get("videoCount")),
                    "view_count": _integer(stats.get("viewCount")),
                })
        return {"videos": videos, "channels": channels, "source": "youtube_data_api_v3"}
    finally:
        if own:
            client.close()


def _integer(value: Any) -> int | None:
    try:
        number = int(value)
        return number if number >= 0 else None
    except (ValueError, TypeError):
        return None


def _normal(text: str) -> str:
    return " ".join(str(text).replace("<", "").replace(">", "").split())


def _tokens(text: str) -> set[str]:
    return {word.casefold() for word in _WORDS.findall(text) if len(word) >= 3
            and word.casefold() not in _STOP}


def _titles(topic: str, language: str, original_title: str = "") -> list[str]:
    topic = _normal(topic)
    if not topic:
        raise SEOError("A nonempty topic is required")
    if language.lower().startswith("es"):
        candidates = [original_title, topic, f"{topic}: guía práctica", f"{topic} explicado"]
    else:
        candidates = [original_title, topic, f"{topic}: a practical guide", f"{topic} explained"]
    output = []
    for candidate in candidates:
        candidate = _normal(candidate)
        if 0 < len(candidate) <= 100 and candidate.casefold() not in (x.casefold() for x in output):
            output.append(candidate)
    return output[:4]


def build_review(
    *, topic: str, region: str, language: str, public_data: dict[str, Any],
    original_title: str = "", own_tags: list[str] | None = None,
) -> dict[str, Any]:
    """Competitor observations are advisory; never alter verified script metadata."""
    if not _REGION.fullmatch(region) or not _LANG.fullmatch(language):
        raise SEOError("Invalid region or language")
    videos = public_data.get("videos", [])
    channels = public_data.get("channels", [])
    if not isinstance(videos, list) or not isinstance(channels, list):
        raise SEOError("Invalid offline public-data snapshot")
    topic_tokens = _tokens(topic)
    tag_counts: Counter[str] = Counter()
    for video in videos[:10]:
        if not isinstance(video, dict):
            raise SEOError("Invalid video in snapshot")
        for tag in video.get("tags", [])[:40]:
            if not isinstance(tag, str):
                continue
            tag = _normal(tag)
            if 3 <= len(tag) <= 50 and (_tokens(tag) & topic_tokens):
                tag_counts[tag.casefold()] += 1
    suggested_tags = list(dict.fromkeys(
        t for t in [_normal(topic), *(own_tags or [])]
        if t and len(t) <= 40
    ))[:15]
    observed_tags = [tag for tag, _ in tag_counts.most_common(15)]
    selected_videos = []
    for v in videos[:10]:
        video_id = v.get("id", "")
        if not _VIDEO_ID.fullmatch(str(video_id)):
            continue
        selected_videos.append({
            "title": _normal(v.get("title", ""))[:100],
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "channel": _normal(v.get("channel_title", ""))[:100],
            "published_at": v.get("published_at", ""),
            "views_public_snapshot": _integer(v.get("view_count")),
            "likes_public_snapshot": _integer(v.get("like_count")),
            "comments_public_snapshot": _integer(v.get("comment_count")),
            "public_tags_available": bool(v.get("tags")),
        })
    return {
        "status": "NEEDS_OWNER_REVIEW",
        "source": public_data.get("source", "user_imported_snapshot"),
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "topic": _normal(topic),
        "target_region": region, "preferred_language": language,
        "region_note": "regionCode filters video availability; it does not measure where viewers are located",
        "title_candidates_not_verified": _titles(topic, language, original_title),
        "suggested_tags_from_own_topic": suggested_tags,
        "observed_competitor_tags_not_recommended_automatically": observed_tags,
        "public_videos": selected_videos,
        "public_channels": channels[:10],
        "video_count": len(selected_videos),
        "guardrails": [
            "No automatic title/tag replacement, posting, uploads, purchase or API access without opt-in",
            "No view, RPM, keyword-volume or ranking predictions",
            "Competitor content is never evidence for script factual claims",
            "Owner must separately review SEO suggestions, research and final release",
        ],
    }


def telegram_summary(report: dict[str, Any]) -> str:
    lines = [
        "YouTube SEO Intelligence — OWNER REVIEW",
        f"{report['topic']} | {report['preferred_language']} | {report['target_region']}",
        f"Observed videos: {report['video_count']}",
        "Candidate titles (not approved):",
    ]
    lines += ["- " + title for title in report["title_candidates_not_verified"][:3]]
    for video in report["public_videos"][:3]:
        views = video["views_public_snapshot"]
        lines += [f"{video['title']} | views: {views if views is not None else 'hidden'}",
                  video["url"]]
    lines += ["Review required. No uploads, scraping, or promises about growth.",
              "US region search is not proof that viewers are in the US."]
    return "\n".join(lines)[:3800]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only YouTube SEO review: Alan7 and LogicScript")
    parser.add_argument("--topic", required=True)
    parser.add_argument("--region", default="US")
    parser.add_argument("--language", default="en")
    parser.add_argument("--max-results", type=int, default=8)
    parser.add_argument("--video-url", default="")
    parser.add_argument("--channel-id", default="")
    parser.add_argument("--snapshot", type=Path, help="Offline JSON {videos, channels}; no API key needed")
    parser.add_argument("--live", action="store_true", help="Explicit opt-in; uses official YouTube API")
    parser.add_argument("--draft", type=Path, help="Existing draft folder with script.json; advisory only")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.live == bool(args.snapshot):
        parser.error("Choose exactly one input: --live or --snapshot")
    if args.live:
        data = collect_public_videos(
            api_key=os.environ.get("YOUTUBE_API_KEY", ""),
            query="" if args.video_url or args.channel_id else args.topic,
            video_url=args.video_url, channel_id=args.channel_id,
            region=args.region, language=args.language, max_results=args.max_results,
        )
    else:
        data = json.loads(args.snapshot.read_text(encoding="utf-8"))
    own_tags, original_title = [], ""
    if args.draft:
        from pipeline.models import ScriptArtifact
        from .metadata import derive_tags
        script = ScriptArtifact.model_validate_json((args.draft / "script.json").read_text(encoding="utf-8"))
        if script.topic.casefold().strip() != args.topic.casefold().strip():
            parser.error("--topic must match the approved draft topic")
        own_tags = derive_tags(script)
        original_title = script.title
    report = build_review(topic=args.topic, region=args.region, language=args.language,
                          public_data=data, own_tags=own_tags, original_title=original_title)
    if args.out.exists():
        parser.error("Output directory already exists; refuse to overwrite review evidence")
    args.out.mkdir(parents=True)
    (args.out / "seo_review.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (args.out / "telegram_review.txt").write_text(telegram_summary(report), encoding="utf-8")
    print(json.dumps({"review": str(args.out / "seo_review.json"),
                      "telegram": str(args.out / "telegram_review.txt"),
                      "status": report["status"], "videos": report["video_count"],
                      "published": False, "applied_to_metadata": False}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
