"""Offline adapter tests. No network, no API keys required."""
from __future__ import annotations
import json
from typing import Any, Callable
import httpx
import pytest
from pydantic import BaseModel
from adapters import (GEMINI_CONFIG,GROQ_CONFIG,OPENROUTER_CONFIG,ConfigurationError,GeminiAdapter,GroqAdapter,LLMRequest,OpenRouterAdapter,SchemaValidationError)
from adapters.rate_limit import RateLimiter
class Answer(BaseModel):
    answer: str
    confidence: float

def _body(text: str, model: str = "test-model") -> dict[str, Any]:
    return {"id": "chatcmpl-test", "object": "chat.completion", "model": model,
            "choices": [{"index": 0, "message": {"role": "assistant", "content": text}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}}

def _adapter(cls: type,config,handler: Callable[[httpx.Request], httpx.Response],*,sleep: Callable[[float],None]|None=None,monotonic:Callable[[],float]|None=None,api_key: str="test-key"):
    kwargs:dict[str,Any]={"api_key":api_key,"transport":httpx.MockTransport(handler)}
    if sleep is not None:kwargs["sleep"]=sleep
    if monotonic is not None:kwargs["monotonic"]=monotonic
    return cls(config,**kwargs)
@pytest.mark.parametrize("cls,config",[(GroqAdapter,GROQ_CONFIG),(GeminiAdapter,GEMINI_CONFIG),(OpenRouterAdapter,OPENROUTER_CONFIG)])
def test_success_path_parses_and_validates(cls,config):
    payload_text=json.dumps({"answer":"ok","confidence":0.9})
    def handler(request:httpx.Request)->httpx.Response:return httpx.Response(200,json=_body(payload_text))
    adapter=_adapter(cls,config,handler)
    response=adapter.complete(LLMRequest(messages=[{"role":"user","content":"hi"}],schema=Answer))
    assert isinstance(response.parsed,Answer)
    assert response.parsed.answer=="ok"
    assert response.parsed.confidence==pytest.approx(0.9)
    assert response.attempts_used == 1
    assert response.provider==config.name
    assert response.usage["total_tokens"]==15

def test_retry_after_is_respected():
    sleeps:list[float]=[]; calls={"n":0}; clock=[0.0]
    def fake_sleep(s):
        sleeps.append(s); clock[0] += s
    def fake_clock(): return clock[0]
    def handler(request:httpx.Request)->httpx.Response:
        calls["n"]+=1
        if calls["n"]==1:return httpx.Response(429,headers={"Retry-After":"2"},json={"error":{"message":"rate limited"}})
        return httpx.Response(200,json=_body(json.dumps({"answer":"ok","confidence":0.5})))
    adapter=_adapter(GroqAdapter,GROQ_CONFIG,handler,sleep=fake_sleep,monotonic=fake_clock)
    response=adapter.complete(LLMRequest(messages=[{"role":"user","content":"hi"}],schema=Answer))
    assert response.parsed is not None and response.parsed.answer=="ok"
    assert response.attempts_used == 2
    assert calls["n"]==2
    assert any(s>=2.0 for s in sleeps),sleeps

def test_5xx_retries_then_succeeds():
    sleeps:list[float]=[];calls={"n":0}
    def handler(request:httpx.Request)->httpx.Response:
        calls["n"]+=1
        if calls["n"]<3:return httpx.Response(502,json={"error":"bad gateway"})
        return httpx.Response(200,json=_body(json.dumps({"answer":"ok","confidence":1.0})))
    adapter=_adapter(GeminiAdapter,GEMINI_CONFIG,handler,sleep=sleeps.append)
    response=adapter.complete(LLMRequest(messages=[{"role":"user","content":"hi"}],schema=Answer))
    assert response.attempts_used == 3
    assert calls["n"]==3
    assert response.parsed is not None and response.parsed.confidence==1.0
    assert len(sleeps)>=2
    assert sleeps[1]>sleeps[0]

def test_schema_validation_failure():
    def handler(request:httpx.Request)->httpx.Response:return httpx.Response(200,json=_body('{"answer": "ok"}'))
    adapter=_adapter(OpenRouterAdapter,OPENROUTER_CONFIG,handler)
    with pytest.raises(SchemaValidationError):adapter.complete(LLMRequest(messages=[{"role":"user","content":"hi"}],schema=Answer))

def test_non_json_response_raises():
    def handler(request:httpx.Request)->httpx.Response:return httpx.Response(200,json=_body("not json at all"))
    adapter=_adapter(GroqAdapter,GROQ_CONFIG,handler)
    with pytest.raises(SchemaValidationError):adapter.complete(LLMRequest(messages=[{"role":"user","content":"hi"}],schema=Answer))

def test_markdown_fences_are_stripped():
    fenced="```json\n"+json.dumps({"answer":"ok","confidence":0.1})+"\n```"
    def handler(request:httpx.Request)->httpx.Response:return httpx.Response(200,json=_body(fenced))
    adapter=_adapter(GeminiAdapter,GEMINI_CONFIG,handler)
    response=adapter.complete(LLMRequest(messages=[{"role":"user","content":"hi"}],schema=Answer))
    assert response.parsed is not None and response.parsed.answer=="ok"

def test_missing_api_key_raises(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY",raising=False)
    def handler(request:httpx.Request)->httpx.Response:return httpx.Response(200,json=_body("{}"))
    with pytest.raises(ConfigurationError):GroqAdapter(GROQ_CONFIG,api_key=None,transport=httpx.MockTransport(handler))

def test_groq_payload_contains_json_keyword():
    captured:dict[str,Any]={}
    def handler(request:httpx.Request)->httpx.Response:
        captured["payload"]=json.loads(request.content.decode("utf-8"))
        return httpx.Response(200,json=_body(json.dumps({"answer":"ok","confidence":0.2})))
    adapter=_adapter(GroqAdapter,GROQ_CONFIG,handler)
    adapter.complete(LLMRequest(messages=[{"role":"user","content":"hi"}],schema=Answer))
    blob=json.dumps(captured["payload"]["messages"]).lower()
    assert "json" in blob
    assert captured["payload"]["response_format"]=={"type":"json_object"}

def test_openrouter_headers(monkeypatch):
    monkeypatch.setenv("OPENROUTER_HTTP_REFERER","https://example.test")
    monkeypatch.setenv("OPENROUTER_X_TITLE","RouterV3-Test")
    captured:dict[str,Any]={}
    def handler(request:httpx.Request)->httpx.Response:
        captured["headers"]=dict(request.headers)
        return httpx.Response(200,json=_body(json.dumps({"answer":"ok","confidence":0.3})))
    adapter=_adapter(OpenRouterAdapter,OPENROUTER_CONFIG,handler)
    adapter.complete(LLMRequest(messages=[{"role":"user","content":"hi"}],schema=Answer))
    assert captured["headers"]["http-referer"]=="https://example.test"
    assert captured["headers"]["x-title"]=="RouterV3-Test"

def test_rate_limiter_blocks_after_rpm():
    clock=[0.0]; sleeps:list[float]=[]
    def sleep(seconds:float)->None:sleeps.append(seconds);clock[0]+=seconds
    def monotonic()->float:return clock[0]
    limiter=RateLimiter(rpm=2,rpd=10,monotonic=monotonic,sleep=sleep)
    limiter.acquire();limiter.acquire();limiter.acquire()
    assert any(s>=59.0 for s in sleeps),sleeps

def test_rate_limiter_penalize():
    clock=[0.0];sleeps:list[float]=[]
    def sleep(seconds:float)->None:sleeps.append(seconds);clock[0]+=seconds
    def monotonic()->float:return clock[0]
    limiter=RateLimiter(rpm=100,rpd=100,monotonic=monotonic,sleep=sleep)
    limiter.penalize(5.0);limiter.acquire()
    assert any(s>=4.9 for s in sleeps),sleeps
