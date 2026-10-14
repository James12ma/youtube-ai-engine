"""Extra tests exposing security and retry defects in DeepSeek's Task 2.
All cases use MockTransport; no live API request is made.
"""
from dataclasses import replace
import json
import httpx
import pytest
from pydantic import BaseModel
from adapters import (OPENROUTER_CONFIG, GROQ_CONFIG, GEMINI_CONFIG,
                      GroqAdapter, GeminiAdapter, OpenRouterAdapter, LLMRequest,
                      ConfigurationError, ServerError)

class Answer(BaseModel):
    answer: str
    confidence: float

OK={"choices":[{"message":{"content":json.dumps({"answer":"ok","confidence":0.9})}}]}
REQ=LLMRequest(messages=[{"role":"user","content":"Return JSON"}],schema=Answer)

def test_openrouter_paid_model_rejected_before_network():
    calls=[]
    def mock(req):
        calls.append(req)
        return httpx.Response(200,json=OK)
    a=OpenRouterAdapter(api_key="test",transport=httpx.MockTransport(mock))
    with pytest.raises(ConfigurationError):
        a.complete(LLMRequest(messages=REQ.messages, schema=Answer, model="openai/gpt-4o"))
    assert calls==[]

def test_retry_requests_count_against_rpm():
    clock=[0.]
    def monotonic():return clock[0]
    def sleep(s):clock[0]+=s
    count=[0]
    def mock(req):
        count[0]+=1
        return httpx.Response(502,json={"error":"bad gateway"}) if count[0]==1 else httpx.Response(200,json=OK)
    a=GroqAdapter(replace(GROQ_CONFIG,rpm=1,rpd=10,max_retries=2),api_key="test",transport=httpx.MockTransport(mock),sleep=sleep,monotonic=monotonic)
    a.complete(REQ)
    assert count[0]==2
    assert clock[0]>=60.0

def test_malformed_200_body_raises_adapter_error():
    a=GeminiAdapter(api_key="test",transport=httpx.MockTransport(lambda req: httpx.Response(200,text="<html>oops</html>")))
    with pytest.raises(ServerError):a.complete(REQ)

def test_schema_validation_one_repair_retry():
    calls=[]
    def mock(req):
        calls.append(json.loads(req.content))
        if len(calls)==1:
            return httpx.Response(200,json={"choices":[{"message":{"content":'{"answer":"ok"}'}}]})
        return httpx.Response(200,json=OK)
    a=GroqAdapter(api_key="test",transport=httpx.MockTransport(mock))
    result=a.complete(REQ)
    assert result.parsed.answer=='ok'
    assert len(calls)==2
    assert 'confidence' in json.dumps(calls[1]['messages'])

def test_503_respects_retry_after():
    clock=[0.]
    def monotonic():return clock[0]
    def sleep(s):clock[0]+=s
    count=[0]
    def mock(req):
        count[0]+=1
        if count[0]==1:return httpx.Response(503,headers={"Retry-After":"15"},json={"error":"maintenance"})
        return httpx.Response(200,json=OK)
    a=GroqAdapter(replace(GROQ_CONFIG,max_retries=2),api_key="test",transport=httpx.MockTransport(mock),sleep=sleep,monotonic=monotonic)
    a.complete(REQ)
    assert clock[0]>=15.0

def test_default_live_network_disabled_even_with_key(monkeypatch):
    monkeypatch.delenv("ENABLE_LIVE_LLM", raising=False)
    with pytest.raises(ConfigurationError):
        GroqAdapter(api_key="dummy-key")

def test_paid_model_override_via_environment_rejected(monkeypatch):
    monkeypatch.setenv("OPENROUTER_MODEL", "anthropic/claude-sonnet-4")
    seen=[]
    def mock(req):
        seen.append(req)
        return httpx.Response(200,json=OK)
    adapter=OpenRouterAdapter(api_key="dummy",transport=httpx.MockTransport(mock))
    with pytest.raises(ConfigurationError):
        adapter.complete(REQ)
    assert not seen

def test_groq_default_uses_model_reviewed_on_free_plan():
    seen=[]
    def mock(req):
        seen.append(json.loads(req.content)["model"])
        return httpx.Response(200,json=OK)
    a=GroqAdapter(api_key="test",transport=httpx.MockTransport(mock))
    a.complete(REQ)
    assert seen == ["openai/gpt-oss-120b"]

def test_very_long_429_backoff_halts_without_sleep():
    times=[]
    def mock(req):
        return httpx.Response(429,headers={"Retry-After":"3600"},json={"error":"quota"})
    from adapters import RateLimitError
    a=GroqAdapter(api_key="test",transport=httpx.MockTransport(mock),sleep=times.append)
    with pytest.raises(RateLimitError) as e:
        a.complete(REQ)
    assert e.value.retry_after == 3600.0
    assert not times

def test_local_day_exhaustion_does_not_sleep_for_24_hours():
    from adapters import RateLimitError
    from adapters.rate_limit import RateLimiter
    clock = [0.0]
    sleeps = []
    limiter = RateLimiter(
        rpm=10, rpd=1, monotonic=lambda: clock[0],
        sleep=lambda secs: sleeps.append(secs),
    )
    limiter.acquire(max_wait_seconds=60)
    with pytest.raises(RateLimitError) as caught:
        limiter.acquire(max_wait_seconds=60)
    assert caught.value.retry_after >= 86000
    assert sleeps == []
