"""Contract tests for grounded cinematic scenes. Free and offline."""
import hashlib
import json
import pytest

from tiktok_motion.premium_job import make_plan
from tiktok_motion.story_scene import enrich_visual, STORY_KINDS


def test_all_new_visual_kinds_are_recognized():
    assert STORY_KINDS == {"character", "device", "signal_flow", "document", "data", "map", "hero"}


def test_owner_storyboard_preserves_spoken_text_and_scene_continuity(tmp_path):
    raw = {
        "title": "Applicant to recruiter",
        "scenes": [
            {"narration": "The applicant calls the recruiter.",
             "kind": "signal_flow", "flow": {"from": "Applicant phone", "to": "Recruiter phone"},
             "setting": "Office network", "action": "The recruiter receives a notification.",
             "camera": "pan_right"},
            {"narration": "The recruiter and applicant talk.",
             "kind": "character", "actors": ["Applicant", "Recruiter"], "camera": "push_in"},
        ],
    }
    script = json.dumps(raw)
    plan = make_plan({"script": script}, tmp_path)
    assert [s["narration"] for s in plan["scenes"]] == [x["narration"] for x in raw["scenes"]]
    assert plan["scenes"][0]["flow"] == {"from": "Applicant phone", "to": "Recruiter phone"}
    assert plan["scenes"][1]["actors"] == ["Applicant", "Recruiter"]
    assert plan["source_sha256"] == hashlib.sha256(script.encode()).hexdigest()
    assert plan["auto_publish"] is False
    assert plan["requires_owner_approval"] is True


@pytest.mark.parametrize("scene", [
    {"kind": "signal_flow"},
    {"kind": "signal_flow", "flow": {"from": "Phone", "to": ""}},
    {"kind": "character"},
    {"kind": "document"},
    {"kind": "data"},
    {"kind": "data", "data": [{"label": "Revenue", "value": float("nan")}]},
    {"kind": "data", "data": [{"label": "Revenue", "value": -10}]},
    {"kind": "data", "data": [{"label": "Revenue", "value": True}]},
    {"kind": "data", "data": [{"label": "Revenue", "value": "100"}]},
    {"kind": "data", "data": [{"label": "Revenue", "value": 10, "source": "invented"}]},
    {"kind": "device", "camera": "teleport"},
    {"kind": "hero", "actors": ["Repeated", "Repeated"]},
    {"kind": "hero", "flow": {"to": "X", "secret": "Y"}},
])
def test_unsafe_or_ungrounded_visual_plans_fail_closed(scene):
    with pytest.raises(ValueError):
        enrich_visual(scene)


def test_explicit_supplied_measurements_and_excerpt_pass():
    assert enrich_visual({"kind": "data", "data": [{"label": "Users", "value": 17}]})["data"] == [{"label": "Users", "value": 17}]
    assert enrich_visual({"kind": "document", "excerpt": "Confirmed original quote", "source_label": "Owner supplied"})["excerpt"] == "Confirmed original quote"


def test_legacy_kinds_remain_available(tmp_path):
    script = "One paragraph remains the original renderer without invented visual subjects or story roles."
    plan = make_plan({"script": script}, tmp_path)
    assert plan["scenes"][0]["kind"] == "kinetic"
    assert plan["scenes"][0]["actors"] == []
    assert plan["scenes"][0]["data"] == []


def test_no_external_asset_urls_or_unapproved_story_kinds():
    with pytest.raises(ValueError, match="Unsupported"):
        enrich_visual({"kind": "ai_generated_full_3d"})
