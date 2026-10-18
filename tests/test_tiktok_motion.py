"""Contract tests for the independent TikTok planning module."""
import copy
import unittest

from tiktok_motion import build_demo, validate_storyboard


class TikTokMotionTests(unittest.TestCase):
    def test_demo_contract(self):
        demo = build_demo()
        self.assertEqual((demo["width"], demo["height"], demo["fps"]), (1080, 1920, 30))
        self.assertEqual(len(demo["scenes"]), 6)
        self.assertEqual(demo["duration_seconds"], 60)
        self.assertFalse(demo["auto_publish"])
        self.assertTrue(demo["requires_owner_approval"])

    def test_timeline_gap_rejected(self):
        demo = copy.deepcopy(build_demo())
        demo["scenes"][1]["start_seconds"] = 6
        with self.assertRaises(ValueError):
            validate_storyboard(demo)

    def test_publish_gate_rejected(self):
        demo = copy.deepcopy(build_demo())
        demo["auto_publish"] = True
        with self.assertRaises(ValueError):
            validate_storyboard(demo)


if __name__ == "__main__":
    unittest.main()
