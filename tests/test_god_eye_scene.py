"""Contract tests: God's Eye View extension cannot silently fake a map scene."""
import pytest

from tiktok_motion.story_scene import enrich_visual


def scene(**changes):
    value = {
        "kind": "god_eye",
        "narration": "Across the world, whale migrations follow ocean routes.",
        "geo_clip": "job/god_eye_whales.mp4",
        "geo_attribution": "Source: reviewed Cesium capture; imagery terms cleared",
        "camera": "orbit",
    }
    value.update(changes)
    return value


def test_accepts_reviewed_local_geographic_capture():
    enriched = enrich_visual(scene())
    assert enriched["geo_clip"] == "job/god_eye_whales.mp4"
    assert "Source:" in enriched["geo_attribution"]


@pytest.mark.parametrize("filename", [
    "https://example.org/video.mp4", "../secrets.mp4",
    "job/god_eye_../../etc/passwd", "job/god_eye_whales.mov",
    "job/another.mp4",
])
def test_blocks_unapproved_capture_path(filename):
    with pytest.raises(ValueError, match="reviewed local"):
        enrich_visual(scene(geo_clip=filename))


def test_requires_source_attribution():
    with pytest.raises(ValueError, match="attribution"):
        enrich_visual(scene(geo_attribution=""))


def test_rejects_decorative_geography():
    with pytest.raises(ValueError, match="geographically"):
        enrich_visual(scene(narration="A person clicks a button on a phone."))


def test_does_not_allow_geo_asset_in_unrelated_scene():
    with pytest.raises(ValueError, match="Only a god_eye"):
        enrich_visual(scene(kind="hero"))


def test_existent_map_scenes_are_preserved():
    assert enrich_visual({"kind": "map", "camera": "push_in"})["geo_clip"] == ""
