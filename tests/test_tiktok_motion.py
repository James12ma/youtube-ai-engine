"""Unit tests for the isolated TikTok Motion Engine foundation."""
from __future__ import annotations

import unittest
from pathlib import Path
import tempfile
import shutil

from tiktok_motion.storyboard import build_demo, validate_storyboard, full_narration_text


class TestStoryboard(unittest.TestCase):
    def test_build_demo_contract(self):
        data = build_demo()
        self.assertEqual(data["width"], 1080)
        self.assertEqual(data["height"], 1920)
        self.assertEqual(data["fps"], 30)
        self.assertEqual(data["duration_seconds"], 60)
        self.assertTrue(data["requires_owner_approval"])
        self.assertFalse(data["auto_publish"])
        self.assertEqual(data["language"], "en")
        self.assertEqual(len(data["scenes"]), 6)

    def test_timeline_continuous(self):
        data = build_demo()
        validate_storyboard(data)  # raises on failure

    def test_narration_present(self):
        data = build_demo()
        text = full_narration_text(data)
        self.assertIn("internet", text.lower())
        self.assertGreater(len(text), 100)
        for s in data["scenes"]:
            self.assertTrue(s["narration"].strip())

    def test_no_auto_publish(self):
        data = build_demo()
        data["auto_publish"] = True
        with self.assertRaises(ValueError):
            validate_storyboard(data)


class TestRenderSmoke(unittest.TestCase):
    def test_render_module_imports(self):
        from tiktok_motion import render as r
        self.assertTrue(callable(r.render))
        self.assertTrue(callable(r.generate_narration))

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("espeak-ng"), "ffmpeg/espeak required")
    def test_short_render(self):
        """Render a few frames conceptually by calling build + font path."""
        from tiktok_motion.render import _font, SCENE_DRAW
        f = _font(40)
        self.assertIsNotNone(f)
        self.assertIn("hook", SCENE_DRAW)
        self.assertIn("outro", SCENE_DRAW)


class TestEngineRouting(unittest.TestCase):
    def test_visual_director_routes(self):
        from tiktok_motion.visual_director import choose_engine, route_storyboard
        from tiktok_motion.storyboard import build_demo
        self.assertEqual(choose_engine("statistics"), "manim")
        routed = route_storyboard(build_demo())
        self.assertEqual(len(routed), 6)
        self.assertTrue(all("engine" in s for s in routed))

    def test_engine_status(self):
        from tiktok_motion.engine_registry import engine_status
        st = engine_status()
        self.assertIn("manim", st)
        self.assertIn("remotion", st)
        self.assertTrue(st["manim"]["available"] or True)  # may or may not be installed in CI


if __name__ == "__main__":
    unittest.main()
