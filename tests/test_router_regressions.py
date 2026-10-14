"""Additional fail-closed / durable-state checks for Router V3.1, offline only."""
from __future__ import annotations
import subprocess
from pathlib import Path
from types import SimpleNamespace
import pytest
from pydantic import BaseModel
from adapters import LLMRequest
from router import Router, RouterConfig, RouterPaused, AllProvidersFailed
from router.runtime import RouterRuntimeStore
from state_store import StateStore, SensitiveStateError
class Answer(BaseModel): message: str
def repo(path):
    path.mkdir()
    for args in [('init','-b','main'),('config','user.name','T'),('config','user.email','t@e.i')]:
        subprocess.run(['git',*args],cwd=path,check=True,capture_output=True)
    (path/'.gitignore').write_text('.router-state/\n.router-locks/\n')
    (path/'README.md').write_text('repo')
    for args in [('add','.'),('commit','-m','init')]:
        subprocess.run(['git',*args],cwd=path,check=True,capture_output=True)
    return path
class Fake:
    def __init__(self,provider='groq', model=None, replies=('one',), attempts=1):
        self.config=SimpleNamespace(name=provider,default_model=model or {'groq':'openai/gpt-oss-120b','gemini':'gemini-2.5-flash','openrouter':'foo:free'}[provider], max_retries=attempts,model_env_var=provider.upper()+'_MODEL')
        self.calls=0;self.replies=iter(replies)
    def complete(self,req):
        self.calls+=1
        return SimpleNamespace(parsed=Answer(message=next(self.replies)))
def request(txt='test'):return LLMRequest(messages=[{'role':'user','content':txt}],schema=Answer)
def make(path,adapters,**opts):
    return Router(StateStore(path,push_required=False),adapters,RouterConfig(**opts))
@pytest.fixture(autouse=True)
def allow(monkeypatch):monkeypatch.setenv('ROUTER_ALLOW_LIVE_API','1')
def test_environment_model_override_rejected_before_dispatch(tmp_path,monkeypatch):
    p=repo(tmp_path/'repo');monkeypatch.setenv('GROQ_MODEL','paid/not-allowed')
    bad=Fake('groq');good=Fake('gemini')
    result=make(p,{'groq':bad,'gemini':good}).execute('test',{'id':1},request(),Answer)
    assert result.message=='one' and bad.calls==0 and good.calls==1

def test_persistent_daily_quota_is_enforced(tmp_path):
    p=repo(tmp_path/'repo');a=Fake('groq',replies=('one','two'))
    rt=make(p,{'groq':a},rpd={'groq':1},rpm={'groq':5},all_failed_pause=1)
    assert rt.execute('one',{'id':1},request(),Answer).message=='one'
    with pytest.raises(AllProvidersFailed):rt.execute('one',{'id':2},request(),Answer)
    assert a.calls==1

def test_pessimistic_retry_quota(tmp_path):
    p=repo(tmp_path/'repo');a=Fake('groq',attempts=3)
    router=make(p,{'groq':a},rpd={'groq':4},rpm={'groq':4})
    router.execute('one',{'id':1},request(),Answer)
    rt=router._runtime_store.load()
    assert rt['quotas']['groq']['count']==3
    with pytest.raises(AllProvidersFailed):router.execute('one',{'id':2},request('different'),Answer)
    assert a.calls==1

def test_prompt_change_invalidates_cache(tmp_path):
    p=repo(tmp_path/'repo');a=Fake('groq',replies=('one','two'))
    router=make(p,{'groq':a})
    assert router.execute('same',{'id':1},request('alpha'),Answer).message=='one'
    assert router.execute('same',{'id':1},request('beta'),Answer).message=='two'
    assert a.calls==2

def test_claim_exclusivity_and_crashed_claim_expiry(tmp_path):
    p=repo(tmp_path/'repo');a=Fake('groq');router=make(p,{'groq':a})
    router._task_lease('xyz','owner-a',1000)
    with pytest.raises(RouterPaused):router._task_lease('xyz','owner-b',1010)
    router._task_lease('xyz','owner-b',2000)
    assert router._runtime_store.load()['leases']['xyz']['owner']=='owner-b'

def test_runtime_rejects_sensitive_payload(tmp_path):
    p=repo(tmp_path/'repo')
    runtime=RouterRuntimeStore(StateStore(p,push_required=False))
    with pytest.raises(SensitiveStateError):
        runtime.transact(lambda rt: rt.update(authorization='Bearer totally-secret'),operation_id='bad-state')

def test_invalid_model_not_mistaken_for_outage(tmp_path):
    p=repo(tmp_path/'repo');a=Fake('groq',model='not-free')
    router=make(p,{'groq':a})
    with pytest.raises(AllProvidersFailed):router.execute('one',{'id':1},request(),Answer)
    assert a.calls==0
    assert not router._runtime_store.load().get('circuit_breakers',{}).get('groq')

def test_half_open_probe_exclusivity_does_not_consume_quota(tmp_path):
    p=repo(tmp_path/'repo');a=Fake('groq');router=make(p,{'groq':a})
    router._runtime_store.transact(lambda rt: rt.update(circuit_breakers={'groq':{'state':'open','failure_count':3,'opened_at':0}},half_open_probes={'groq':'other-task'}))
    assert router._reserve_provider('groq','my-task',2000,'res-1',1) is False
    assert not router._runtime_store.load().get('quotas',{}).get('groq')

def test_stale_half_open_probe_is_recovered_after_crash(tmp_path):
    p=repo(tmp_path/'repo')
    router=make(p,{'groq':Fake('groq')})
    def crashed_state(rt):
        rt.update(half_open_probes={'groq':'old-task'},leases={'old-task':{'owner':'dead','until':10}})
    router._runtime_store.transact(crashed_state)
    router._task_lease('new-task','alive',2000)
    state=router._runtime_store.load()
    assert state['half_open_probes']=={}
    assert state['leases']['new-task']['owner']=='alive'
