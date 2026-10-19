"""SEO editorial-package tests: offline, no paid LLM and no publishing."""
import json
import pytest
from channel.seo_package import propose_editorial_package, telegram_editorial_package
from channel.seo_intelligence import main as seo_main


def test_documentary_package_is_bounded_unverified_and_source_labeled():
    observations = [
        {"title": "Ballenas jorobadas: acrobacias en el mar", "tags": ["NatGeo"]},
        {"title": "Alimentación de ballenas jorobadas", "tags": []},
    ]
    pkg = propose_editorial_package(
        "ballenas jorobadas", "es", "documentary", observations
    )
    assert len(pkg["titles_unapproved"]) == 5
    assert len(set(pkg["titles_unapproved"])) == 5
    assert all(len(x) <= 100 for x in pkg["titles_unapproved"])
    assert pkg["generator"] == "deterministic_templates_no_llm"
    assert pkg["status"] == "NEEDS_OWNER_REVIEW"
    assert pkg["uploaded"] is False and pkg["applied_to_release"] is False
    assert "acrobacias" in [x["theme"] for x in pkg["observed_competitor_title_themes_not_facts"]]
    assert "[añadir" in pkg["description_unapproved"]
    assert len(pkg["hashtags_unapproved"]) == 3
    assert all(x.startswith("#") for x in pkg["hashtags_unapproved"])
    assert "NatGeo" not in str(pkg["keywords_unapproved"])
    assert "apwouve" in telegram_editorial_package(pkg)


def test_logicscript_tutorial_package_without_fabricated_demonstration():
    pkg = propose_editorial_package(
        "Excel expense tracker", "en", "tutorial",
        [{"title": "Expense tracker Excel tutorial"}],
        draft_title="How to Build an Expense Tracker", draft_hook="Let's open Excel.",
    )
    assert len(pkg["titles_unapproved"]) == 5
    assert "step-by-step" in pkg["titles_unapproved"][0]
    assert "on screen" in pkg["hook_unapproved"]
    assert "[insert a reviewed screen demonstration]" in pkg["description_unapproved"]
    assert pkg["draft_title_preserved"] == "How to Build an Expense Tracker"
    assert pkg["draft_hook_preserved"] == "Let's open Excel."
    assert pkg["requires_verified_script"] is True
    assert pkg["requires_footage_or_screen_demo_review"] is True


def test_long_and_html_topics_are_sanitized_and_bounded():
    pkg = propose_editorial_package("<div>" + "Ballenas " * 20 + "</div>", "es",
                                    "documentary", [])
    assert all(len(t) <= 100 for t in pkg["titles_unapproved"])
    assert "<" not in pkg["hook_unapproved"] and ">" not in str(pkg)
    assert pkg["sample_size"] == 0


def test_bad_mode_and_short_topic_fail_closed():
    with pytest.raises(ValueError, match="mode"):
        propose_editorial_package("ballenas", "es", "publish", [])
    with pytest.raises(ValueError, match="short"):
        propose_editorial_package("a", "es", "documentary", [])


@pytest.mark.parametrize("mode", ["documentary", "tutorial"])
def test_existing_seo_cli_generates_review_and_package_without_api_or_release(
    tmp_path, monkeypatch, capsys, mode
):
    monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
    snap = tmp_path / "sample.json"
    snap.write_text(json.dumps({"source": "offline_fixture", "videos": [
        {"id": "A1b2C3d4E5F", "title": "Guía visual de ballenas jorobadas",
         "view_count": 500, "tags": ["Ballenas"], "channel_title": "Sample"},
    ], "channels": []}), encoding="utf-8")
    out = tmp_path / ("report_" + mode)
    assert seo_main(["--topic", "ballenas jorobadas", "--snapshot", str(snap),
                     "--language", "es", "--mode", mode, "--out", str(out)]) == 0
    pkg = json.loads((out / "seo_editorial_package.json").read_text())
    assert pkg["channel_mode"] == mode
    assert len(pkg["titles_unapproved"]) == 5
    assert (out / "seo_review.json").is_file()
    assert (out / "seo_editorial_telegram.txt").is_file()
    assert json.loads(capsys.readouterr().out)["published"] is False
