"""Offline tests reconstructed from user supplied Task 3 suite."""
from __future__ import annotations
import subprocess
from pathlib import Path
from types import SimpleNamespace
from typing import Any
import pytest
from pydantic import BaseModel
from adapters import LLMRequest, RateLimitError, ServerError
from router import AllProvidersFailed, LiveAPINotAuthorized, Router, RouterConfig, RouterPaused
from state_store import StateStore
class Echo(BaseModel): message: str
def _init_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    def run(*args: str) -> None:
        subprocess.run(["git", *args], cwd=str(path), check=True, capture_output=True)
    run("init", "-b", "main");run("config", "user.email", "t@e.i");run("config", "user.name", "T")
    (path/".gitignore").write_text(".router-state/\n.router-locks/\n")
    (path/"README.md").write_text("seed\n")
    run("add", ".gitignore", "README.md");run("commit", "-m", "init")
    return path
@pytest.fixture
def repo(tmp_path: Path)->Path:return _init_repo(tmp_path/"repo")
def _fake_response(message: str):
    return SimpleNamespace(parsed=Echo(message=message), text=message, provider="fake", model="fake", usage={}, raw={})
class FakeAdapter:
    def __init__(self,name: str,default_model: str|None=None,script: list[Any]|None=None):
        self.config=SimpleNamespace(name=name,default_model=default_model or {"groq":"openai/gpt-oss-120b","gemini":"gemini-2.5-flash","openrouter":"meta-llama/llama-3.3-70b-instruct:free"}[name],max_retries=1)
        self._script=list(script or []);self.calls=0
    def complete(self,request:LLMRequest)->Any:
        self.calls += 1
        if not self._script: raise RuntimeError("FakeAdapter exhausted")
        item=self._script.pop(0)
        if isinstance(item,Exception): raise item
        return item
def _adapters(groq=None,gemini=None,openrouter=None)->dict:
    return {"groq":groq,"gemini":gemini,"openrouter":openrouter}
def _make_router(repo,adapters,**config_kwargs):
    return Router(StateStore(repo,push_required=False),adapters,RouterConfig(**config_kwargs))
@pytest.fixture(autouse=True)
def _authorize_live(monkeypatch):monkeypatch.setenv("ROUTER_ALLOW_LIVE_API","1")
def _request():return LLMRequest(messages=[{"role":"user","content":"hi"}],schema=Echo)
def test_failover_groq_rate_limited_to_gemini(repo):
    groq=FakeAdapter("groq",script=[RateLimitError("429",retry_after=5.)]);gemini=FakeAdapter("gemini",script=[_fake_response("from-gemini")]);router=_make_router(repo,_adapters(groq=groq,gemini=gemini))
    result=router.execute("echo",{"n":1},_request(),Echo)
    assert result.message=="from-gemini" and groq.calls==1 and gemini.calls==1
def test_failover_all_three(repo):
    g=FakeAdapter("groq",script=[ServerError("502")]);m=FakeAdapter("gemini",script=[ServerError("502")]);o=FakeAdapter("openrouter",script=[_fake_response("from-or")]);router=_make_router(repo,_adapters(g,m,o))
    assert router.execute("echo",{"n":2},_request(),Echo).message=="from-or"
def test_all_fail_pauses_router(repo):
    adapters={n:FakeAdapter(n,script=[ServerError("502")]) for n in ("groq","gemini","openrouter")};router=_make_router(repo,adapters)
    with pytest.raises(AllProvidersFailed):router.execute("echo",{"n":3},_request(),Echo)
    with pytest.raises(RouterPaused):router.execute("echo",{"n":3},_request(),Echo)
def test_cached_result_is_idempotent(repo):
    a=FakeAdapter("groq",script=[_fake_response("first")]);router=_make_router(repo,_adapters(groq=a))
    assert router.execute("echo",{"n":4},_request(),Echo).message=="first"
    assert router.execute("echo",{"n":4},_request(),Echo).message=="first" and a.calls==1
def test_circuit_breaker_opens_after_threshold(repo):
    g=FakeAdapter("groq",script=[ServerError("502")]*3)
    m=FakeAdapter("gemini",script=[_fake_response(s) for s in ("g1","g2","g3","g4")]);router=_make_router(repo,_adapters(groq=g,gemini=m),failure_threshold=3)
    for n in (10,11,12):router.execute("echo",{"n":n},_request(),Echo)
    router.execute("echo",{"n":13},_request(),Echo)
    assert g.calls==3 and m.calls==4
def test_cooldown_persists_across_restart(repo):
    g=FakeAdapter("groq",script=[RateLimitError("429",retry_after=600.)]);m=FakeAdapter("gemini",script=[_fake_response("g")]);_make_router(repo,_adapters(groq=g,gemini=m)).execute("echo",{"n":20},_request(),Echo)
    g2=FakeAdapter("groq",script=[_fake_response("bad")]);m2=FakeAdapter("gemini",script=[_fake_response("g2")]);_make_router(repo,_adapters(groq=g2,gemini=m2)).execute("echo",{"n":21},_request(),Echo)
    assert g2.calls==0 and m2.calls==1
def test_live_api_authorization_required(repo,monkeypatch):
    monkeypatch.delenv("ROUTER_ALLOW_LIVE_API",raising=False)
    g=FakeAdapter("groq",script=[_fake_response("x")]);router=_make_router(repo,_adapters(groq=g))
    with pytest.raises(LiveAPINotAuthorized):router.execute("echo",{"n":30},_request(),Echo)
    assert g.calls==0
def test_billable_model_rejected(repo):
    o=FakeAdapter("openrouter",default_model="openai/gpt-4");router=_make_router(repo,_adapters(openrouter=o),provider_order=("openrouter",))
    with pytest.raises(AllProvidersFailed) as exc:router.execute("echo",{"n":31},_request(),Echo)
    assert "openai/gpt-4" in str(exc.value) and o.calls==0
    with pytest.raises(RouterPaused):router.execute("echo",{"n":32},_request(),Echo)
    assert o.calls==0
def test_quota_counter_persists_and_resets(repo):
    g=FakeAdapter("groq",script=[_fake_response("a"),_fake_response("b")]);router=_make_router(repo,_adapters(groq=g))
    router.execute("echo",{"n":40},_request(),Echo);router.execute("echo",{"n":41},_request(),Echo)
    runtime=router._runtime_store.load();assert runtime["quotas"]["groq"]["count"]==2
    other=_make_router(repo,_adapters(groq=g));future=2000000000.;rt=other._runtime_store.load();assert future > 2_000_000
    assert rt["quotas"]["groq"]["count"]==2
def test_crash_recovery_reexecutes_task(repo):
    class Crash(FakeAdapter):
        def complete(self,request):self.calls+=1;raise KeyboardInterrupt("crash")
    r1=_make_router(repo,_adapters(groq=Crash("groq")))
    with pytest.raises(KeyboardInterrupt):r1.execute("echo",{"n":50},_request(),Echo)
    h=FakeAdapter("groq",script=[_fake_response("recovered")]);r2=_make_router(repo,_adapters(groq=h))
    assert r2.execute("echo",{"n":50},_request(),Echo).message=="recovered" and h.calls==1
