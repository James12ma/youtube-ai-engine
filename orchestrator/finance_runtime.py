"""Opt-in, zero-cost-only finance Router adapter for the existing premium job.

The original owner script MUST already have been fetched from Telegram and
verified against the SHA-256 before finance_payload is called.
"""
from __future__ import annotations

import os
from pathlib import Path

from adapters import (
    GROQ_CONFIG, GEMINI_CONFIG, OPENROUTER_CONFIG,
    GroqAdapter, GeminiAdapter, OpenRouterAdapter,
)
from router import Router, RouterConfig
from state_store import StateStore
from .finance_planner import plan, to_premium_script


def finance_payload(owner_data: dict) -> dict:
    if os.environ.get("FINANCE_LLM_APPROVED") != "1":
        raise ValueError("Finance LLM provider use has not been explicitly approved")
    if os.environ.get("ROUTER_ALLOW_LIVE_API") != "1" or os.environ.get("ENABLE_LIVE_LLM") != "1":
        raise ValueError("Live Router access is disabled")
    if owner_data.get("profile") != "premium" or owner_data.get("language", "en") != "en":
        raise ValueError("Unsupported finance narration profile")
    adapter_classes = {
        "groq": (GroqAdapter, GROQ_CONFIG),
        "gemini": (GeminiAdapter, GEMINI_CONFIG),
        "openrouter": (OpenRouterAdapter, OPENROUTER_CONFIG),
    }
    adapters = {}
    try:
        for name, (cls, cfg) in adapter_classes.items():
            if os.environ.get(cfg.env_var):
                adapters[name] = cls(config=cfg)
        if not adapters:
            raise ValueError("No approved free-tier API key configured")
        # This Git state store is isolated to the branch runner. No remote push.
        state = StateStore(Path.cwd(), push_required=False)
        router = Router(state, adapters,
                        RouterConfig(provider_order=tuple(adapters)))
        storyboard = plan(owner_data["script"], router)
        return {
            "script": to_premium_script(storyboard),
            "visual_mode": "premium",
            "profile": "premium",
            "language": "en",
            "voice": owner_data.get("voice", "af_heart"),
        }
    finally:
        for adapter in adapters.values():
            adapter.close()
