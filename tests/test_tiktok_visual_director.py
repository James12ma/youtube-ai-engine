import unittest
from unittest.mock import patch
from tiktok_motion.visual_director import choose_engine, route_storyboard
from tiktok_motion.storyboard import build_demo

class VisualDirectorTests(unittest.TestCase):
    @patch("tiktok_motion.visual_director.available_engines", return_value={x:{"available":True} for x in ("manim","motion_canvas","remotion","pillow")})
    def test_specialized_routes(self,_status):
        self.assertEqual(choose_engine("map"), "motion_canvas")
        self.assertEqual(choose_engine("chart"), "manim")
        self.assertEqual(choose_engine("hook"), "remotion")
    @patch("tiktok_motion.visual_director.available_engines", return_value={})
    def test_unavailable_renderers_fall_back_honestly(self,_status):
        self.assertEqual(choose_engine("chart"),"pillow")
        self.assertEqual(choose_engine("map"),"pillow")

    def test_preserve_existing_engines(self):
        self.assertEqual(choose_engine("chart", "screen_tutorial"), "logicscript")
        self.assertEqual(choose_engine("map", "documentary"), "alan7")
    def test_all_scenes_routed(self):
        self.assertEqual(len(route_storyboard(build_demo())), 6)

if __name__ == "__main__":
    unittest.main()
