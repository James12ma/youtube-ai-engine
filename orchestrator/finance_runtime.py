"""Opt-in, zero-cost-only finance Router adapter for the existing premium job.

The original owner script MUST already have been fetched from Telegram and
verified against the SHA-256 before finance_payload is called.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

from adapters import GROQ_CONFIG, GroqAdapter
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
    # Only Groq Free Plan is approved for this pilot.
    if os.environ.get("FINANCE_FREE_PROVIDER") != "groq":
        raise ValueError("Finance pilot is restricted to Groq Free Plan")
    if not os.environ.get("GROQ_API_KEY"):
        raise ValueError("GROQ_API_KEY has not been configured")
    adapters = {}
    try:
        adapters["groq"] = GroqAdapter(config=GROQ_CONFIG)
        # Review job: isolated Git repo without remotes or inherited credentials.
        # No cross-run cache; avoid touching the shared production router-state branch.
        with tempfile.TemporaryDirectory(prefix="finance-router-") as work:
            subprocess.run(["git", "init", "-q", work], check=True,
                           capture_output=True)
            state = StateStore(Path(work), push_required=False)
            router = Router(state, adapters,
                            RouterConfig(provider_order=("groq",)))
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
