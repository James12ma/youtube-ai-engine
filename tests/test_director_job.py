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
