"""Local tool detection; never auto-installs paid or remote services."""
from __future__ import annotations

from .engines.adapters import available_engines


def engine_status() -> dict:
    return available_engines()
