"""Fast offline checks for the reference video producer (no rendering or spending)."""
import unittest
from tiktok_motion.reference15.produce import W,H,FPS,SECONDS,alpha,ease,entrance,frame


class EditorialReferenceTests(unittest.TestCase):
    def test_video_timeline(self):
        self.assertEqual((W,H,FPS,SECONDS),(720,1280,30,15))
        self.assertEqual(SECONDS*FPS,450)

    def test_easing_bounds(self):
        self.assertEqual(ease(-1),0)
        self.assertEqual(ease(2),1)
        self.assertEqual(entrance(0,1),0)
        self.assertEqual(alpha(1,2,3),0)

    def test_scene_changes_are_animated(self):
        a=frame(2);b=frame(6);c=frame(10);d=frame(14)
        self.assertEqual(a.size,(W,H))
        self.assertTrue(all(i.mode=='RGB' for i in (a,b,c,d)))
        self.assertNotEqual(a.tobytes(),b.tobytes())
        self.assertNotEqual(b.tobytes(),c.tobytes())
        self.assertNotEqual(c.tobytes(),d.tobytes())

if __name__=='__main__':unittest.main()
