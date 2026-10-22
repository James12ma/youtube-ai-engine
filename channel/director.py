"""Evidence-linked offline AI Director review: verified script + storyboard + SEO.

This is a deterministic director integration over artifacts from the EXISTING source
verification pipeline. It DOES NOT invent facts, run an LLM, alter artifacts,
record screens, approve rendering or publish. Competitor SEO is advisory only.
"""
from __future__ import annotations
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlparse

from pipeline.models import ScriptArtifact, ResearchArtifact, StoryboardOutput
from verification.models import VerificationGateReport
from .metadata import generate_metadata, ReleaseMetadata


class DirectorBlocked(ValueError):
    """Missing evidence, mismatched artifacts, or unsafe unsupported edit."""


_THEMES = {
    "en": ("build", "automate", "from scratch", "in minutes", "template",
           "guide", "step by step", "tracker", "tutorial"),
    "es": ("construye", "automatiza", "desde cero", "en minutos",
           "documental", "ballenas", "comportamiento", "vida", "acrobacias"),
}


def _safe(text: str, limit: int = 150) -> str:
    return " ".join(str(text).replace("<", "").replace(">", "").split())[:limit].strip()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _check_storyboard(script: ScriptArtifact, storyboard: StoryboardOutput, accepted: set[str]) -> None:
    if not storyboard.scenes:
        raise DirectorBlocked("Storyboard is empty")
    for scene in storyboard.scenes:
        if scene.section_index < 0 or scene.section_index >= len(script.sections):
            raise DirectorBlocked("Storyboard scene references nonexistent script section")
        if scene.claim_ids and set(scene.claim_ids) - accepted:
            raise DirectorBlocked("Storyboard cites unaccepted claim")


def _themes(videos: list[dict], lang: str) -> list[dict]:
    """Observed competitor *title* phrases only; never ranked causal signals."""
    texts = []
    for video in videos[:10]:
        if not isinstance(video, dict):
            continue
        title = video.get("title", video.get("snippet", {}).get("title", ""))
        texts.append(_safe(title, 110).casefold())
    return [
        {"phrase": phrase, "titles_mentioning": sum(phrase in title for title in texts)}
        for phrase in _THEMES[lang]
        if sum(phrase in title for title in texts)
    ]


def _title_options(script: ScriptArtifact, mode: str, has_screen_plan: bool) -> list[str]:
    """Only promise concepts present in the verified script, not a rival's title."""
    title = _safe(script.title, 100)
    topic = _safe(script.topic, 70)
    headings = [_safe(section.heading, 40) for section in script.sections if section.heading.strip()]
    lang = "es" if script.language.lower().startswith("es") else "en"
    # Do not imply visuals that do not at least appear in the storyboard.
    lead = "Guía de " if lang == "es" else "Guide to "
    choices = [title]
    if headings:
        choices.append(f"{title} | {headings[0]}")
    if len(headings) >= 2:
        choices.append(f"{topic}: {headings[0]} + {headings[1]}")
    if mode == "tutorial" and has_screen_plan and len(script.sections) >= 2:
        choices.append(f"{topic} | {'Paso a paso' if lang == 'es' else 'Step-by-step walkthrough'}")
    if len(headings) >= 3:
        choices.append(f"{lead}{topic}: {headings[1]} + {headings[2]}")
    if len(headings) >= 2:
        choices.append(f"{lead}{topic} | {headings[-1]}")
    unique, seen = [], set()
    for choice in choices:
        candidate = _safe(choice, 100).rstrip(" |:,+")
        if candidate and candidate.casefold() not in seen:
            seen.add(candidate.casefold())
            unique.append(candidate)
    return unique[:5]


def director_bundle(
    draft_dir: Path, *, mode: str, competitor_data: dict | None = None
) -> dict:
    if mode not in ("tutorial", "documentary"):
        raise DirectorBlocked("Unknown mode")
    draft_dir = Path(draft_dir)
    required = ("research.json", "script.json", "storyboard.json", "verification_gate.json")
    blobs = {}
    for name in required:
        file = draft_dir / name
        if not file.is_file() or file.is_symlink():
            raise DirectorBlocked(f"Verified draft file missing or unsafe: {name}")
        blobs[name] = file.read_bytes()
    try:
        research = ResearchArtifact.model_validate_json(blobs["research.json"])
        script = ScriptArtifact.model_validate_json(blobs["script.json"])
        storyboard = StoryboardOutput.model_validate_json(blobs["storyboard.json"])
        gate = VerificationGateReport.model_validate_json(blobs["verification_gate.json"])
    except Exception as exc:
        raise DirectorBlocked(f"Invalid verified draft artifacts: {type(exc).__name__}") from None
    if script.topic != research.topic or gate.topic != script.topic:
        raise DirectorBlocked("Script, research and verification topics differ")
    if script.language not in ("en", "es"):
        raise DirectorBlocked("Unsupported script language")
    if not script.sections or not script.hook.strip():
        raise DirectorBlocked("No verified script sections or hook")
    if gate.contradictions.pairs or gate.traceability.unverified_cited_claims or gate.traceability.uncited_numeric_sections:
        raise DirectorBlocked("Unresolved contradiction or citation problems")
    accepted = {v.claim_id for v in gate.verdicts if v.accepted}
    used = {cid for section in script.sections for cid in section.claim_ids}
    if not accepted or not used or used - accepted:
        raise DirectorBlocked("Script references unaccepted or missing claims")
    cited = {c.claim_id for c in gate.traceability.citations}
    if not used.issubset(cited):
        raise DirectorBlocked("Script claims missing verification traceability")
    _check_storyboard(script, storyboard, accepted)
    # The existing metadata generator revalidates accepted claims and HTTPS source URLs.
    try:
        metadata: ReleaseMetadata = generate_metadata(script, research, gate)
    except Exception as exc:
        raise DirectorBlocked("Existing metadata verification failed: " + str(type(exc).__name__)) from None
    if len(metadata.description.encode("utf-8")) > 5000:
        raise DirectorBlocked("Metadata violates YouTube byte limit")
    if mode == "tutorial" and script.language != "en":
        # This is not a YouTube rule; guard against accidentally using an EN format
        # for a Spanish documentary when a production route was mis-selected.
        pass
    screen_plan = any(scene.visual_type == "screen_recording" for scene in storyboard.scenes)
    visual_plan = [{
        "section_index": scene.section_index,
        "visual_type": scene.visual_type,
        "instruction": _safe(scene.instruction, 240),
        "planned_only_not_recorded": True,
    } for scene in storyboard.scenes[:25]]
    public_videos = []
    if competitor_data is not None:
        if not isinstance(competitor_data, dict) or not isinstance(competitor_data.get("videos"), list):
            raise DirectorBlocked("SEO snapshot requires a videos array")
        public_videos = competitor_data["videos"][:10]
    themes = _themes(public_videos, script.language)
    candidate_titles = _title_options(script, mode, screen_plan)
    section_previews = [{
        "heading": section.heading,
        "narration": section.narration,
        "claim_ids": section.claim_ids,
    } for section in script.sections]
    source_urls = []
    for cite in gate.traceability.citations:
        if cite.claim_id in used:
            for url in cite.source_urls:
                p = urlparse(url)
                if p.scheme != "https" or not p.hostname:
                    raise DirectorBlocked("Non-HTTPS source in gate")
                if url not in source_urls:
                    source_urls.append(url)
    if not source_urls:
        raise DirectorBlocked("No traceable source URLs")
    return {
        "status": "OWNER_REVIEW_REQUIRED",
        "director_kind": "verified_artifact_bridge_not_a_live_llm",
        "topic": script.topic, "language": script.language, "mode": mode,
        "evidence": {"sha256": {name: _sha256(data) for name, data in blobs.items()},
                     "accepted_script_claim_ids": sorted(used), "source_urls": source_urls[:12]},
        "competitive_observations": {
            "status": "public_title_sample_only" if public_videos else "no_public_sample",
            "sample_size": len(public_videos),
            "observed_title_phrases_not_ranking_predictions": themes,
        },
        "verified_script": {"title": script.title, "hook": script.hook,
                            "sections": section_previews, "cta": script.cta},
        "metadata_from_existing_verified_pipeline": metadata.model_dump(mode="json"),
        "title_alternatives_unapproved": candidate_titles,
        "hook_proposal": script.hook, "hook_provenance": "unchanged_verified_script",
        "visual_storyboard_planned_not_recorded": visual_plan,
        "screen_capture_planned": screen_plan,
        "real_screen_capture_verified": False,
        "real_footage_verified": False,
        "editorial_approval": False,
        "render_approved": False,
        "uploaded": False,
        "review_required": [
            "Verify evidence and exact source URLs independently",
            "Review proposed title against the recorded/sourced visual sequence",
            "Review full existing verified script, hook and narration",
            "Supply and inspect real screen capture or licensed footage before final render",
            "Obtain owner's explicit release approval before upload",
        ],
    }


def phone_review(bundle: dict) -> str:
    lines = [
        "AI DIRECTOR — VERIFIED DRAFT / OWNER REVIEW",
        f"{bundle['mode']} | {bundle['language']} | {bundle['topic']}",
        f"Script: {len(bundle['verified_script']['sections'])} verified sections",
        "Title ideas (unapproved):",
        *["- " + t for t in bundle["title_alternatives_unapproved"]],
        "Verified script hook (unchanged):", bundle["verified_script"]["hook"],
        "Section headings (from verified script):",
        *["- " + item["heading"] for item in bundle["verified_script"]["sections"][:7]],
        "Observed competitor phrases, not ranking evidence:",
    ]
    themes = bundle["competitive_observations"]["observed_title_phrases_not_ranking_predictions"]
    lines.extend(["- " + t["phrase"] + " (" + str(t["titles_mentioning"]) + " titles)" for t in themes[:5]]
                 or ["No competitor samples provided"])
    lines.extend(["REVIEW REQUIRED. Script evidence is preserved. Actual screen/footage unverified.",
                  "No render approved; no upload, no payment."])
    return "\n".join(lines)[:3900]


def director_cli(draft: Path, out: Path, mode: str, snapshot: Path | None = None) -> dict:
    """Fail closed: no partial output, no changes to the original draft."""
    out = Path(out)
    if out.exists():
        raise DirectorBlocked("Output already exists; no replacement of earlier evidence")
    observations = json.loads(Path(snapshot).read_text(encoding="utf-8")) if snapshot else None
    bundle = director_bundle(draft, mode=mode, competitor_data=observations)
    out.mkdir(parents=True)
    (out / "director_review.json").write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "telegram_review.txt").write_text(phone_review(bundle), encoding="utf-8")
    return {"status": bundle["status"], "review": str(out / "director_review.json"),
            "telegram": str(out / "telegram_review.txt"), "published": False, "render_approved": False}
