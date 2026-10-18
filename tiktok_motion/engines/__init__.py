"""Rendering engine adapters for TikTok Motion Engine.

Manim Community (MIT) is fully integrated when installed.
Remotion and Motion Canvas adapters are present but require local npm
install; the sandbox currently cannot fetch packages (npm 502).
"""
from .adapters import render_scene, available_engines

__all__ = ["render_scene", "available_engines"]
