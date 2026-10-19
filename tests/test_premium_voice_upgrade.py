"""Quality gate: premium narration cannot silently fall back to eSpeak."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from tiktok_motion.reference15.premium_voice import SCENES, DURATION, _compose, replace_voice


class PremiumVoiceTests(TestCase):
    def test_scenes_cover_98_seconds(self):
        self.assertEqual(len(SCENES), 7)
        self.assertEqual(SCENES[0][0], 0)
        self.assertEqual(SCENES[-1][1], DURATION)
        self.assertTrue(all(a[1] == b[0] for a,b in zip(SCENES, SCENES[1:])))

    def test_model_required_no_robot_voice(self):
        with TemporaryDirectory() as td:
            video = Path(td) / "source.mp4"
            video.write_bytes(b"placeholder")
            with self.assertRaisesRegex(FileNotFoundError, "refusing robotic eSpeak"):
                replace_voice(video, Path(td) / "missing.onnx", Path(td) / "new.mp4")

    def test_original_not_overwritten(self):
        with TemporaryDirectory() as td:
            video = Path(td) / "source.mp4"
            video.write_bytes(b"placeholder")
            model = Path(td) / "voice.onnx"
            model.write_bytes(b"placeholder")
            Path(str(model) + ".json").write_text("{}")
            with self.assertRaisesRegex(ValueError, "separate"):
                replace_voice(video, model, video)

    def test_all_seven_segments_required(self):
        with TemporaryDirectory() as td:
            with self.assertRaisesRegex(ValueError, "One narration WAV"):
                _compose([], Path(td) / "result.wav")
