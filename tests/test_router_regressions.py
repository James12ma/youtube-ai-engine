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

class Clock:
    def __init__(self):
        self.now = 1000.0
        self.waits = []
    def __call__(self):
        return self.now
    def sleep(self, seconds):
        self.waits.append(seconds)
        self.now += seconds


def test_director_18_of_20_reservations_waits_then_repairs(tmp_path):
    """Reproduce run 39337749774 without any provider/network calls."""
    p = repo(tmp_path/'repo')
    clock = Clock()
    adapter = Fake('openrouter', attempts=3)
    router = Router(StateStore(p, push_required=False), {'openrouter': adapter},
                    RouterConfig(local_quota_wait_s=65), clock=clock, sleep=clock.sleep)
    def historical(rt):
        rt.update(cooldowns={'groq':87400, 'gemini':87400},
                  quotas={'openrouter':{'minute':[980.0]*18, 'day':[980.0]*24}})
    router._runtime_store.transact(historical)
    result = router.execute('pipeline.script_section', {'repair':1}, request(), Answer)
    assert result.message == 'one' and adapter.calls == 1
    assert 40 <= sum(clock.waits) <= 41
    assert max(clock.waits) <= 30
    runtime = router._runtime_store.load()
    assert len(runtime['quotas']['openrouter']['minute']) == 3
    assert len(runtime['quotas']['openrouter']['day']) == 27
    assert not runtime.get('paused_until')
    assert runtime['leases'] == {}


def test_daily_quota_does_not_wait_or_dispatch(tmp_path):
    p = repo(tmp_path/'repo'); clock = Clock(); adapter = Fake('openrouter', attempts=3)
    router = Router(StateStore(p,push_required=False), {'openrouter':adapter},
                    RouterConfig(local_quota_wait_s=65), clock=clock, sleep=clock.sleep)
    router._runtime_store.transact(lambda rt:rt.update(
        quotas={'openrouter':{'minute':[980.0]*18,'day':[980.0]*48}}))
    with pytest.raises(AllProvidersFailed, match='local quota'):
        router.execute('test',{},request(),Answer)
    assert clock.waits == [] and adapter.calls == 0


def test_available_fallback_runs_before_waiting(tmp_path):
    p = repo(tmp_path/'repo'); clock = Clock()
    groq = Fake('groq', attempts=3); gemini = Fake('gemini')
    router = Router(StateStore(p,push_required=False), {'groq':groq,'gemini':gemini},
                    RouterConfig(local_quota_wait_s=65), clock=clock, sleep=clock.sleep)
    router._runtime_store.transact(lambda rt:rt.update(
        quotas={'groq':{'minute':[990.0]*30,'day':[990.0]*30}}))
    assert router.execute('test',{},request(),Answer).message == 'one'
    assert groq.calls == 0 and gemini.calls == 1 and clock.waits == []


def test_wait_budget_shorter_than_window_fails_without_dispatch(tmp_path):
    p = repo(tmp_path/'repo'); clock = Clock(); adapter = Fake('openrouter', attempts=3)
    router = Router(StateStore(p,push_required=False), {'openrouter':adapter},
                    RouterConfig(local_quota_wait_s=5), clock=clock, sleep=clock.sleep)
    router._runtime_store.transact(lambda rt:rt.update(
        quotas={'openrouter':{'minute':[999.0]*18,'day':[999.0]*18}}))
    with pytest.raises(AllProvidersFailed):
        router.execute('test',{},request(),Answer)
    assert sum(clock.waits) == 5 and adapter.calls == 0
    assert router._runtime_store.load()['leases'] == {}


def test_client_error_does_not_disable_provider_for_24_hours(tmp_path):
    from adapters import ClientError
    p = repo(tmp_path/'repo')
    class ClientFailure(Fake):
        def complete(self, req):
            self.calls += 1
            raise ClientError('provider: non-retryable HTTP 400')
    adapter = ClientFailure('groq')
    router = make(p, {'groq':adapter}, all_failed_pause=0)
    with pytest.raises(AllProvidersFailed):
        router.execute('test',{},request(),Answer)
    runtime = router._runtime_store.load()
    assert 'groq' not in runtime.get('cooldowns',{})
    assert runtime['circuit_breakers']['groq']['failure_count'] == 0


def test_auth_error_retains_24_hour_cooldown(tmp_path):
    from adapters import AuthError
    p = repo(tmp_path/'repo')
    class AuthFailure(Fake):
        def complete(self, req):
            raise AuthError('provider: authentication/permissions error 401')
    router = make(p, {'groq':AuthFailure('groq')})
    with pytest.raises(AllProvidersFailed):
        router.execute('test',{},request(),Answer)
    assert router._runtime_store.load()['cooldowns']['groq'] > __import__('time').time() + 86300


def test_only_proven_unused_retries_are_refunded_once(tmp_path):
    p = repo(tmp_path/'repo'); adapter = Fake('openrouter', attempts=3)
    router = make(p, {'openrouter':adapter})
    assert router._reserve_provider('openrouter','task',1000,'reservation',3)
    router._settle_successful_reservation('reservation',1)
    router._settle_successful_reservation('reservation',1)
    runtime=router._runtime_store.load()
    assert runtime['quotas']['openrouter']['minute'] == [1000]
    assert runtime['quotas']['openrouter']['day'] == [1000]
    assert runtime['quotas']['openrouter']['count'] == 1
    assert runtime['reservations']['reservation']['attempts_charged'] == 1


@pytest.mark.parametrize('used',[None,0,4,True])
def test_unknown_or_invalid_attempt_count_stays_fully_reserved(tmp_path,used):
    p = repo(tmp_path/'repo'); router = make(p, {'openrouter':Fake('openrouter',attempts=3)})
    assert router._reserve_provider('openrouter','task',1000,'reservation',3)
    router._settle_successful_reservation('reservation',used)
    assert router._runtime_store.load()['quotas']['openrouter']['count'] == 3


def test_success_settles_actual_http_attempts_before_next_request(tmp_path):
    import httpx
    from adapters import OpenRouterAdapter, OPENROUTER_CONFIG
    p=repo(tmp_path/'repo'); clock=Clock(); requests=[]
    def handler(req):
        requests.append(req)
        return httpx.Response(200,json={'choices':[{'message':{'content':'{"message":"ok"}'}}]})
    adapter=OpenRouterAdapter(OPENROUTER_CONFIG,api_key='offline-only',transport=httpx.MockTransport(handler))
    try:
        router=Router(StateStore(p,push_required=False),{'openrouter':adapter},
                      RouterConfig(rpd={'openrouter':4},rpm={'openrouter':4},local_quota_wait_s=65),
                      clock=clock,sleep=clock.sleep)
        for index in range(2):
            assert router.execute('test',{'index':index},request(),Answer).message == 'ok'
        assert len(requests) == 2 and clock.waits == []
        assert router._runtime_store.load()['quotas']['openrouter']['count'] == 2
    finally:
        adapter.close()


def test_schema_failure_does_not_globally_pause_unrelated_tasks(tmp_path):
    from adapters import SchemaValidationError
    p=repo(tmp_path/'repo')
    class InvalidThenValid(Fake):
        def complete(self,req):
            self.calls+=1
            if self.calls==1:
                raise SchemaValidationError('Invalid narration schema')
            return SimpleNamespace(parsed=Answer(message='valid'))
    adapter=InvalidThenValid('openrouter')
    router=make(p,{'openrouter':adapter})
    with pytest.raises(AllProvidersFailed,match='SchemaValidationError'):
        router.execute('bad-content',{},request(),Answer)
    assert not router._runtime_store.load().get('paused_until')
    assert router.execute('different-task',{},request(),Answer).message=='valid'


def test_rate_limit_pause_uses_retry_after_not_hour_long_outage(tmp_path):
    from adapters import RateLimitError
    p=repo(tmp_path/'repo'); clock=Clock()
    class LimitThenValid(Fake):
        def complete(self,req):
            self.calls+=1
            if self.calls==1: raise RateLimitError('rate limited',retry_after=5)
            return SimpleNamespace(parsed=Answer(message='ready'))
    router=Router(StateStore(p,push_required=False),{'openrouter':LimitThenValid('openrouter')},
                  clock=clock,sleep=clock.sleep)
    with pytest.raises(AllProvidersFailed):router.execute('first',{},request(),Answer)
    state=router._runtime_store.load()
    assert state['paused_until']==1005
    assert state['cooldowns']['openrouter']==1005
    clock.sleep(6)
    assert router.execute('next',{},request(),Answer).message=='ready'


def test_blocked_fallback_does_not_hide_client_error_or_pause_router(tmp_path):
    from adapters import ClientError
    p=repo(tmp_path/'repo')
    class BadRequest(Fake):
        def complete(self,req):raise ClientError('groq: non-retryable HTTP 400; reason=invalid_json_generation')
    router=make(p,{'groq':BadRequest('groq'),'openrouter':Fake('openrouter')})
    router._runtime_store.transact(lambda rt:rt.update(cooldowns={'openrouter':__import__('time').time()+600}))
    with pytest.raises(AllProvidersFailed,match='invalid_json_generation'):
        router.execute('test',{},request(),Answer)
    assert not router._runtime_store.load().get('paused_until')
    assert router._runtime_store.load()['circuit_breakers']['groq']['failure_count']==0
