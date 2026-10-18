"""Contract tests for the premium motion prototype timeline (no Blender/Node needed)."""
import json
import unittest
from pathlib import Path

PREMIUM = Path(__file__).resolve().parents[1] / "tiktok_motion" / "premium"
TL = json.loads((PREMIUM / "timeline.json").read_text())


class PremiumTimelineTests(unittest.TestCase):
    def test_vertical_delivery_contract(self):
        self.assertEqual((TL["width"], TL["height"], TL["fps"]), (1080, 1920, 30))
        self.assertTrue(10 <= TL["frames"] / TL["fps"] <= 15)

    def test_beats_inside_timeline_and_ordered(self):
        for name, beat in TL["beats"].items():
            span = beat if isinstance(beat, list) else [beat, beat]
            self.assertLessEqual(span[0], span[1], name)
            self.assertTrue(0 <= span[0] and span[1] <= TL["frames"], name)

    def test_story_order(self):
        b = TL["beats"]
        self.assertLess(b["line1_big"][0], b["dialog_in"][0])
        self.assertTrue(b["dialog_in"][1] < b["cursor_click"] < b["dialog_out"][0])
        self.assertGreaterEqual(b["dots_out"][0], b["cursor_click"])  # nothing disappears before the click
        self.assertLess(b["line2"][1], b["line3"][1])

    def test_copy_matches_scene(self):
        # The dialog promises 24 items: focus_scene.py builds N_DOTS = 24.
        self.assertIn("24 items", TL["copy"]["dialog_body"])
        self.assertIn("N_DOTS = 24", (PREMIUM / "blender" / "focus_scene.py").read_text())


if __name__ == "__main__":
    unittest.main()
