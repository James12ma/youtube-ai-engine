"""Offline, no-network tests for owner-triggered Director workflow request validation."""
import json
import os
import pytest
from scripts.director_job import validate_job, run_job


def payload(topic="Excel expense tracker", lang="en", mode="tutorial", urls=None):
    return json.dumps({
        "topic": topic, "language": lang, "mode": mode,
        "urls": urls or ["https://support.microsoft.com/en-us/excel", "https://learn.microsoft.com/en-us/office/"],
    })


def test_valid_owner_sources_are_accepted_without_api_call():
    req=validate_job(payload(),"a1b2c3d4")
    assert req["topic"]=="Excel expense tracker"
    assert req["mode"]=="tutorial"
    assert len(req["urls"])==2


@pytest.mark.parametrize("urls", [
    ["http://example.com", "https://other.com"],
    ["https://localhost/secret", "https://other.com"],
    ["https://127.0.0.1", "https://other.com"],
    ["https://[::1]/", "https://other.com"],
    ["https://user:password@example.com/a", "https://other.com"],
    ["https://example.com:8080", "https://other.com"],
    ["https://same.example/1", "https://same.example/1"],
])
def test_reject_unsafe_unapproved_sources(urls):
    with pytest.raises(ValueError):
        validate_job(payload(urls=urls),"a1b2c3d4")


def test_reject_unknown_input_and_bad_job_id():
    data=json.loads(payload())
    data["publish"]=True
    with pytest.raises(ValueError):
        validate_job(json.dumps(data),"a1b2c3d4")
    with pytest.raises(ValueError):
        validate_job(payload(),"not-a-job-id")


def test_zero_cost_gates_prevent_live_pipeline_invocation(tmp_path,monkeypatch):
    for key in ("ZERO_COST_ACTIONS_CONFIRMED","FREE_PROVIDER_ACCOUNTS_CONFIRMED",
                "ROUTER_ALLOW_LIVE_API","GROQ_API_KEY","GEMINI_API_KEY","OPENROUTER_API_KEY"):
        monkeypatch.delenv(key,raising=False)
    with pytest.raises(RuntimeError,match="authorization not confirmed"):
        run_job(payload(),"a1b2c3d4",repo=tmp_path,output_root=tmp_path/"out")
    assert not (tmp_path/"out").exists()


def test_no_llm_secret_fails_before_directory_or_network(tmp_path,monkeypatch):
    monkeypatch.setenv("ZERO_COST_ACTIONS_CONFIRMED","1")
    monkeypatch.setenv("FREE_PROVIDER_ACCOUNTS_CONFIRMED","1")
    monkeypatch.setenv("ROUTER_ALLOW_LIVE_API","1")
    for name in ("GROQ_API_KEY","GEMINI_API_KEY","OPENROUTER_API_KEY"):
        monkeypatch.delenv(name,raising=False)
    with pytest.raises(RuntimeError,match="No configured free-tier"):
        run_job(payload(),"a1b2c3d4",repo=tmp_path,output_root=tmp_path/"out")
    assert not (tmp_path/"out").exists()


def test_spanish_documentary_is_explicitly_supported():
    data=validate_job(payload("ballenas jorobadas","es","documentary"),"ee12ac34")
    assert data["language"]=="es"
    assert data["mode"]=="documentary"


def test_preinstall_validation_import_works_without_third_party_site_packages():
    import subprocess
    import sys
    program = ("from scripts.director_job import validate_job; "
               "import json; "
               "validate_job(json.dumps(dict(language='en',mode='tutorial',"
               "topic='Excel expense tracker',urls=['https://example.org/a','https://example.com/b'])),"
               "'f5d48791')")
    output = subprocess.run([sys.executable, "-S", "-c", program],
                            capture_output=True, text=True, check=False)
    assert output.returncode == 0, output.stderr



def test_candidate_is_preserved_on_provider_exhaustion_without_quality_bypass(tmp_path, monkeypatch):
    import channel.research as research
    from router.errors import AllProvidersFailed
    recorded = {"called": 0}

    def rejected_generate(repo, topic, urls, out_dir, *, allow_live, language, mode, unverified_capture):
        recorded["called"] += 1
        assert language == "en" and mode == "tutorial"
        assert allow_live is True
        assert not Path(out_dir).exists()
        Path(unverified_capture).parent.mkdir(parents=True, exist_ok=True)
        Path(unverified_capture).write_text(json.dumps({
            "status": "UNVERIFIED_CANDIDATE",
            "topic": topic, "language": language, "not_approved": True,
            "candidate": {"title": "Actual draft", "hook": "What did you spend?",
                          "sections": [{"heading":"Building the table",
                                        "narration":"This was produced by the free-only research pipeline.",
                                        "claim_ids": []}], "cta": "Review it."}
        }), encoding="utf-8")
        raise AllProvidersFailed("No available approved provider")

    from pathlib import Path
    monkeypatch.setattr(research, "generate_draft", rejected_generate)
    for key in ("ZERO_COST_ACTIONS_CONFIRMED", "FREE_PROVIDER_ACCOUNTS_CONFIRMED",
                "ROUTER_ALLOW_LIVE_API"):
        monkeypatch.setenv(key, "1")
    monkeypatch.setenv("GROQ_API_KEY", "offline-only-placeholder")
    with pytest.raises(AllProvidersFailed):
        run_job(payload(), "f5d48791", repo=tmp_path, output_root=tmp_path/"out")

    folder=tmp_path/"out"/"f5d48791"
    result=json.loads((folder/"failure_review.json").read_text())
    review=(folder/"unverified_candidate_review.txt").read_text()
    assert recorded["called"] == 1
    assert result["status"] == "FAILED_UNVERIFIED"
    assert result["published"] is False and result["rendered"] is False
    assert result["candidate_saved"] is True
    assert "UNVERIFIED SCRIPT CANDIDATE" in review
    assert "Actual draft" in review
    assert "This was produced" in review
    assert "\n" in review
    assert not (folder/"director"/"script_full_review.txt").exists()


def test_no_fake_candidate_or_publish_on_early_failure(tmp_path, monkeypatch):
    import channel.research as research
    def fail_without_candidate(*args,**kwargs):
        raise ValueError("One approved source failed to load")
    monkeypatch.setattr(research, "generate_draft", fail_without_candidate)
    for key in ("ZERO_COST_ACTIONS_CONFIRMED", "FREE_PROVIDER_ACCOUNTS_CONFIRMED",
                "ROUTER_ALLOW_LIVE_API"):
        monkeypatch.setenv(key, "1")
    monkeypatch.setenv("GROQ_API_KEY", "offline-only-placeholder")
    with pytest.raises(ValueError):
        run_job(payload(), "f5d48791", repo=tmp_path, output_root=tmp_path/"out")
    folder=tmp_path/"out"/"f5d48791"
    result=json.loads((folder/"failure_review.json").read_text())
    assert result["candidate_saved"] is False
    assert not (folder/"unverified_candidate_review.txt").exists()


def test_candidate_capture_is_exact_real_script_not_synthetic(tmp_path, monkeypatch):
    import channel.research as research
    from pathlib import Path
    from pipeline.models import ScriptOutput, ScriptSection

    class State:
        def __init__(self, *_args, **_kwargs): pass
    class Provider:
        def __init__(self): pass
        def close(self): pass
    class Router:
        def __init__(self, *_args, **_kwargs): pass
        def execute(self, task_type, *_args):
            assert task_type == "pipeline.script"
            return ScriptOutput(title="Exact candidate", hook="A real hook.",
                 sections=[ScriptSection(heading="First", narration="Short real content.",
                                        claim_ids=[])], cta="The end.")
    class Fetcher:
        def __init__(self, **_kwargs): pass
    class Engine:
        def __init__(self, state, router, fetcher):
            self.router = router
    class Gate:
        def __init__(self, *_args): pass
    class Verified:
        def __init__(self, engine, gate):
            self.engine = engine
        def run(self, topic, urls):
            self.engine.router.execute("pipeline.script", {"topic": topic}, None, ScriptOutput)
            raise ValueError("Quality gate rejected short script")

    monkeypatch.setenv("ROUTER_ALLOW_LIVE_API", "1")
    monkeypatch.setenv("GROQ_API_KEY", "offline-only-placeholder")
    for key in ("GEMINI_API_KEY", "OPENROUTER_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    for name, val in {
        "StateStore":State, "GroqAdapter":Provider, "Router":Router,
        "HttpSourceFetcher":Fetcher, "ContentPipeline":Engine,
        "VerificationGate":Gate, "VerifiedContentPipeline":Verified,
    }.items():
        monkeypatch.setattr(research, name, val)
    capture=tmp_path/"candidate.json"
    with pytest.raises(ValueError,match="Quality gate"):
        research.generate_draft(tmp_path, "Excel expense tracker",
            ["https://example.com/a","https://example.org/b"],tmp_path/"draft",
            allow_live=True, language="en", mode="tutorial", unverified_capture=capture)
    result=json.loads(capture.read_text())
    assert result["status"] == "UNVERIFIED_CANDIDATE"
    assert result["not_approved"] is True
    assert result["source"] == "actual_pipeline_script_response"
    assert result["candidate"]["title"] == "Exact candidate"
    assert len(result["candidate"]["sections"]) == 1
    assert not (tmp_path/"draft"/"script.json").exists()
