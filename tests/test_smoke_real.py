"""Real-network smoke tests. Requires RUN_LLM_SMOKE=1 and ENABLE_LIVE_LLM=1, with manually verified free-tier accounts."""
from __future__ import annotations
import os
import pytest
from pydantic import BaseModel
from adapters import (GEMINI_CONFIG,GROQ_CONFIG,OPENROUTER_CONFIG,GeminiAdapter,GroqAdapter,LLMRequest,OpenRouterAdapter)
pytestmark=[pytest.mark.smoke,pytest.mark.skipif(os.environ.get("RUN_LLM_SMOKE")!="1",reason="set RUN_LLM_SMOKE=1 to enable real-network smoke tests")]
class Ping(BaseModel):
    message:str
def _ping(adapter,config)->None:
    response=adapter.complete(LLMRequest(messages=[{"role":"user","content":'Reply with json {"message":"pong"} and nothing else.'}],schema=Ping,max_tokens=64))
    assert response.provider==config.name
    assert isinstance(response.parsed,Ping)
    assert response.parsed.message
@pytest.mark.skipif(not os.environ.get("GROQ_API_KEY"),reason="GROQ_API_KEY not set")
def test_groq_smoke()->None:_ping(GroqAdapter(GROQ_CONFIG),GROQ_CONFIG)
@pytest.mark.skipif(not os.environ.get("GEMINI_API_KEY"),reason="GEMINI_API_KEY not set")
def test_gemini_smoke()->None:_ping(GeminiAdapter(GEMINI_CONFIG),GEMINI_CONFIG)
@pytest.mark.skipif(not os.environ.get("OPENROUTER_API_KEY"),reason="OPENROUTER_API_KEY not set")
def test_openrouter_smoke()->None:_ping(OpenRouterAdapter(OPENROUTER_CONFIG),OPENROUTER_CONFIG)
