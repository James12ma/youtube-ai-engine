"""Offline contract tests; do NOT download or load Chatterbox model weights."""
import tempfile
import unittest
from pathlib import Path
from tiktok_motion.reference15.chatterbox_voice import BACKENDS, engine_kwargs, replace_with_chatterbox

class CareerChatterboxIntegrationTests(unittest.TestCase):
    def test_chatterbox_en_is_default_english_only(self):
        cfg=engine_kwargs("chatterbox-en")
        self.assertEqual(cfg["language"], "en")
        self.assertTrue(cfg["english_model"])
        self.assertFalse(cfg["latam"])
        self.assertIsNone(cfg["reference_wav"])
        self.assertEqual(cfg["device"], "cpu")

    def test_multilingual_english_not_spanish_finetune(self):
        cfg=engine_kwargs("chatterbox-en-mtl","cuda")
        self.assertEqual(cfg["language"], "en")
        self.assertFalse(cfg["english_model"])
        self.assertFalse(cfg["latam"])
        self.assertEqual(cfg["device"], "cuda")

    def test_reject_non_chatterbox_backends(self):
        self.assertEqual(len(BACKENDS), 2)
        for backend in ("espeak", "piper", "chatterbox", "edge"):
            with self.subTest(backend=backend), self.assertRaisesRegex(ValueError, "English Chatterbox"):
                engine_kwargs(backend)

    def test_reject_invalid_hardware(self):
        with self.assertRaisesRegex(ValueError, "device"):
            engine_kwargs("chatterbox-en", "paid-cloud")

    def test_missing_video_fails_before_loading_model(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(FileNotFoundError, "Source video unavailable"):
                replace_with_chatterbox(Path(d)/"missing.mp4",Path(d)/"new.mp4")

    def test_source_mp4_never_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            v=Path(d)/"source.mp4"
            v.write_bytes(b"sentinel")
            with self.assertRaisesRegex(ValueError, "Never overwrite"):
                replace_with_chatterbox(v,v)
            self.assertEqual(v.read_bytes(), b"sentinel")

if __name__ == "__main__":
    unittest.main()
