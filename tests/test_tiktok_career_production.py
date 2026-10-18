"""Contract tests for the YouTube AI Engine career production entrypoint."""
import shutil
import tempfile
import unittest
from pathlib import Path

from tiktok_motion.produce import TOPICS, normalize_topic, produce

class ProductionProofTests(unittest.TestCase):
    def test_topic_registration(self):
        self.assertEqual(normalize_topic("5 types of job interviews"), "job-interviews")
        self.assertFalse(TOPICS["job-interviews"]["auto_publish"])
        self.assertTrue(TOPICS["job-interviews"]["requires_owner_approval"])

    def test_unknown_topic_fails_loudly(self):
        with tempfile.TemporaryDirectory() as d:
            target=Path(d)/"bad.mp4"
            with self.assertRaisesRegex(ValueError, "Unsupported topic"):
                produce("unverified breaking news",target)
            self.assertFalse(target.exists())

    def test_bad_voice_fails(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError, "voice"):
                produce("job-interviews",Path(d)/"bad.mp4",voice="paid-api")

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),"ffmpeg is required")
    def test_preview_is_produced_by_engine(self):
        with tempfile.TemporaryDirectory() as d:
            target=Path(d)/"career.mp4"
            report=produce("job-interviews",target,preview=True)
            self.assertTrue(target.is_file())
            self.assertGreater(target.stat().st_size,25000)
            self.assertEqual(report["render_status"],"passed")
            self.assertFalse(report["auto_publish"])
            self.assertFalse(report["premium_quality_owner_approved"])
            self.assertTrue(target.with_suffix(".engine_run.json").is_file())

if __name__=="__main__":
    unittest.main()
