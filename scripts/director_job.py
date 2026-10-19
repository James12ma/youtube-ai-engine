"""Owner-triggered source-backed director draft job. Never renders or publishes."""
from __future__ import annotations
import ipaddress
import json
import os
from pathlib import Path
import re
from urllib.parse import urlparse

# Keep module imports stdlib-only: this function is imported BEFORE pip install.
# The verified research/director modules require pydantic and are imported at run time.

_JOB_ID = re.compile(r"^[a-f0-9]{8}$")


def validate_job(raw: str, job_id: str) -> dict:
    if not _JOB_ID.fullmatch(job_id):
        raise ValueError("Invalid director job id")
    if len(raw) > 2200:
        raise ValueError("Director payload exceeds limit")
    data = json.loads(raw)
    if not isinstance(data, dict) or set(data) != {"language", "mode", "topic", "urls"}:
        raise ValueError("Unsupported director draft payload")
    lang, mode, topic, urls = (data[k] for k in ("language", "mode", "topic", "urls"))
    if lang not in ("en", "es") or mode not in ("tutorial", "documentary"):
        raise ValueError("Unsupported director language or mode")
    if not isinstance(topic, str) or not 8 <= len(topic) <= 120 or any(c in topic for c in "<>|\n\r"):
        raise ValueError("Invalid director topic")
    if not isinstance(urls, list) or len(urls) != 2 or len(set(str(u) for u in urls)) != 2:
        raise ValueError("Exactly two distinct source URLs are required")
    for url in urls:
        if not isinstance(url, str) or len(url) > 280:
            raise ValueError("Source URL exceeds limit")
        p = urlparse(url)
        if p.scheme != "https" or not p.hostname or p.username or p.password or p.port not in (None, 443):
            raise ValueError("A public HTTPS source URL without credentials is required")
        host = p.hostname.rstrip(".").lower()
        if host == "localhost" or host.endswith((".localhost", ".local", ".internal", ".test")):
            raise ValueError("Local or internal source URLs are forbidden")
        try:
            ipaddress.ip_address(host)
        except ValueError:
            pass
        else:
            raise ValueError("Literal IP source URLs are forbidden")
    return data


def run_job(raw: str, job_id: str, *, repo: Path, output_root: Path) -> dict:
    payload = validate_job(raw, job_id)
    # Explicit environment allowlist: the GH workflow must confirm free quotas
    # and hold at least one free-tier provider credential before calling this.
    if os.environ.get("ZERO_COST_ACTIONS_CONFIRMED") != "1" or \
       os.environ.get("FREE_PROVIDER_ACCOUNTS_CONFIRMED") != "1" or \
       os.environ.get("ROUTER_ALLOW_LIVE_API") != "1":
        raise RuntimeError("Free-only provider and Actions authorization not confirmed")
    if not any(os.environ.get(k) for k in ("GROQ_API_KEY", "GEMINI_API_KEY", "OPENROUTER_API_KEY")):
        raise RuntimeError("No configured free-tier provider API key; no new draft generated")
    from channel.director import director_cli
    from channel.research import generate_draft
    out = Path(output_root) / job_id
    if out.exists():
        raise RuntimeError("Director job output already exists")
    draft = out / "draft"
    director = out / "director"
    result = generate_draft(
        Path(repo), payload["topic"], payload["urls"], draft,
        allow_live=True, language=payload["language"], mode=payload["mode"],
    )
    final = director_cli(draft, director, payload["mode"])
    script = json.loads((draft / "script.json").read_text(encoding="utf-8"))
    review = [
        "AI DIRECTOR — SCRIPT FOR HUMAN REVIEW",
        "No upload, no final render, no release approval.",
        "Topic: " + script["topic"],
        "Title: " + script["title"],
        "Hook: " + script["hook"],
    ]
    for section in script["sections"]:
        review.extend(["", section["heading"], section["narration"]])
    review.extend(["", "CTA: " + script["cta"],
                   "Review sources, facts, title, visuals and narration before approving."])
    (director / "script_full_review.txt").write_text("\n".join(review), encoding="utf-8")
    return {"status": "OWNER_REVIEW_REQUIRED", "draft": result,
            "director": final, "published": False, "rendered": False,
            "script_file": str(director / "script_full_review.txt")}


def main() -> int:
    job_id = os.environ.get("DIRECTOR_JOB_ID", "")
    raw = os.environ.get("DIRECTOR_JOB_PAYLOAD", "")
    result = run_job(raw, job_id, repo=Path("."), output_root=Path("outputs/director-jobs"))
    print(json.dumps({"status": result["status"], "published": False, "rendered": False,
                      "draft_created": True, "script_ready_for_owner_review": True}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
