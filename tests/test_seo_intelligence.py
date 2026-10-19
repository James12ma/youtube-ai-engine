"""Offline tests only; no live YouTube API calls or publication."""
import json
from pathlib import Path

import httpx
import pytest

from channel.seo_intelligence import (
    SEOError, build_review, collect_public_videos, main, telegram_summary, video_id_from_url,
)

ID1 = "A1b2C3d4E5F"
ID2 = "Q9w8E7r6T5Y"
CH = "UC" + "a" * 22


def mock_client(calls):
    def handler(request):
        path = request.url.path
        calls.append((path, dict(request.url.params)))
        if path.endswith("/search"):
            return httpx.Response(200, json={"items": [
                {"id": {"videoId": ID1}}, {"id": {"videoId": ID2}}
            ]})
        if path.endswith("/videos"):
            return httpx.Response(200, json={"items": [
                {"id": ID1, "snippet": {"title": "Cybersecurity Baseline Tutorial",
                                      "channelId": CH, "channelTitle": "Sample channel",
                                      "tags": ["cybersecurity", "security tutorial"],
                                      "publishedAt": "2026-10-01T00:00:00Z"},
                 "statistics": {"viewCount": "240", "likeCount": "12"},
                 "contentDetails": {"duration": "PT4M"}},
                {"id": ID2, "snippet": {"title": "Unrelated topic", "channelId": CH,
                                      "tags": ["bad topic"]},
                 "statistics": {"viewCount": "2"}},
            ]})
        if path.endswith("/channels"):
            return httpx.Response(200, json={"items": [
                {"id": CH, "snippet": {"title": "Sample channel"},
                 "statistics": {"subscriberCount": "300", "videoCount": "10"}}
            ]})
        return httpx.Response(404)
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_read_only_official_api_max_three_calls():
    calls = []
    with mock_client(calls) as client:
        data = collect_public_videos(
            api_key="NOT-A-REAL-KEY", query="cybersecurity", region="US",
            language="en", client=client,
        )
    assert len(calls) == 3
    assert [path.rsplit("/", 1)[-1] for path, _ in calls] == ["search", "videos", "channels"]
    assert calls[0][1]["part"] == "snippet"
    assert calls[0][1]["regionCode"] == "US"
    assert calls[0][1]["relevanceLanguage"] == "en"
    assert data["videos"][0]["view_count"] == 240
    assert data["channels"][0]["subscriber_count"] == 300
    report = build_review(topic="cybersecurity", region="US", language="en", public_data=data)
    assert report["status"] == "NEEDS_OWNER_REVIEW"
    assert report["video_count"] == 2
    assert "cybersecurity" in report["observed_competitor_tags_not_recommended_automatically"]
    assert "bad topic" not in report["observed_competitor_tags_not_recommended_automatically"]
    assert "viewer" in report["region_note"]
    assert "youtube.com" in telegram_summary(report)


def test_no_key_no_request_and_bounded_search():
    with pytest.raises(SEOError, match="YOUTUBE_API_KEY"):
        collect_public_videos(api_key="", query="cybersecurity")
    with pytest.raises(SEOError, match="max_results"):
        collect_public_videos(api_key="key", query="cybersecurity", max_results=100)
    with pytest.raises(SEOError, match="exactly one"):
        collect_public_videos(api_key="key", query="a", video_url=ID1)


@pytest.mark.parametrize("bad", [
    "http://youtu.be/A1b2C3d4E5F",
    "https://evil-youtube.com/watch?v=A1b2C3d4E5F",
    "https://youtube.com.evil.com/watch?v=A1b2C3d4E5F",
    "https://youtu.be/A1b2C3d4E5F.evil",
])
def test_untrusted_video_urls_rejected(bad):
    with pytest.raises(SEOError):
        video_id_from_url(bad)


def test_known_video_id_and_short_url():
    assert video_id_from_url(f"https://youtu.be/{ID1}") == ID1
    assert video_id_from_url(f"https://www.youtube.com/shorts/{ID1}") == ID1


def test_api_http_error_does_not_echo_key():
    def fail(_request):
        return httpx.Response(403, json={"error": {"message": "secret"}})
    with httpx.Client(transport=httpx.MockTransport(fail)) as client:
        with pytest.raises(SEOError) as exc:
            collect_public_videos(api_key="SUPER_SECRET", query="cybersecurity", client=client)
    assert "SUPER_SECRET" not in str(exc.value)
    assert "403" in str(exc.value)


def test_offline_cli_writes_advisory_without_api_or_upload(tmp_path, monkeypatch, capsys):
    snapshot = tmp_path / "snapshot.json"
    snapshot.write_text(json.dumps({"source": "fixture", "videos": [{
        "id": ID1, "title": "Cybersecurity Sample", "tags": ["cybersecurity", "unrelated"],
        "view_count": 500, "channel_title": "Demo"
    }], "channels": []}), encoding="utf-8")
    monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
    out = tmp_path / "result"
    assert main(["--topic", "cybersecurity", "--snapshot", str(snapshot), "--out", str(out)]) == 0
    report = json.loads((out / "seo_review.json").read_text())
    result = json.loads(capsys.readouterr().out)
    assert result["published"] is False
    assert result["applied_to_metadata"] is False
    assert report["status"] == "NEEDS_OWNER_REVIEW"
    assert (out / "telegram_review.txt").exists()
    with pytest.raises(SystemExit):
        main(["--topic", "cybersecurity", "--snapshot", str(snapshot), "--out", str(out)])


def test_live_requires_explicit_optin(tmp_path):
    with pytest.raises(SystemExit):
        main(["--topic", "test", "--out", str(tmp_path / "report")])
