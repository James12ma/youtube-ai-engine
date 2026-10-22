"""Offline smoke tests for the 98s career motion proof."""
import unittest
from .longform import DURATION,FPS,SEGMENTS,frame

class CareerMotionTests(unittest.TestCase):
    def test_98_seconds_seven_distinct_scenes(self):
        self.assertEqual(DURATION,98)
        self.assertEqual(len(SEGMENTS),7)
        self.assertEqual(SEGMENTS[0][0],0)
        self.assertEqual(SEGMENTS[-1][1],98)
        self.assertTrue(all(a[1]==b[0] for a,b in zip(SEGMENTS,SEGMENTS[1:])))
    def test_full_frame_at_each_scene(self):
        for s,e,*rest in SEGMENTS:
            with self.subTest(scene=s):
                im=frame((s+e)/2)
                self.assertEqual(im.size,(720,1280))
    def test_motion_between_frames(self):
        # Some scene motion is intentionally subtle; not allowed to be a static image.
        for s,e,*rest in SEGMENTS:
            with self.subTest(scene=s):
                a=frame(s+3).tobytes()
                b=frame(s+3.5).tobytes()
                self.assertNotEqual(a,b)
    def test_frame_rate(self):
        self.assertEqual(FPS,30)

if __name__=='__main__':unittest.main()