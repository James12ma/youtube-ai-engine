"""Offline contract tests: owner voice/text is authoritative; never auto publish."""
import json
import tempfile
import unittest
from pathlib import Path

from tiktok_motion.owner_script_input import build_from_owner_file


class OwnerScriptInputTests(unittest.TestCase):
    def test_plaintext_preserves_owner_narration(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "my_notes.txt"
            p.write_text("# My topic\nExact FIRST sentence!\n\nExact second one?", encoding="utf-8")
            data = build_from_owner_file(p)
            self.assertEqual([s["narration"] for s in data["scenes"]],
                             ["Exact FIRST sentence!", "Exact second one?"])
            self.assertTrue(data["requires_owner_approval"])
            self.assertFalse(data["auto_publish"])
            self.assertFalse(data["narration_rewritten"])

    def test_structured_scenes_preserve_visual_notes_and_timing(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "instructions.json"
            p.write_text(json.dumps({"title": "My title", "language": "en", "scenes": [
                {"narration": "My exact words.", "on_screen": "STEP ONE",
                 "kind": "cards", "items": ["Prepare", "Practice"],
                 "visual_notes": "Zoom on card two", "duration_seconds": 8},
                {"narration": "Never change this.", "kind": "process",
                 "items": ["One", "Two"], "duration_seconds": 10},
            ]}))
            data = build_from_owner_file(p)
            self.assertEqual(data["duration_seconds"], 18)
            self.assertEqual(data["scenes"][0]["narration"], "My exact words.")
            self.assertEqual(data["scenes"][1]["start_seconds"], 8)
            self.assertTrue(data["visual_direction_review_required"])
            self.assertEqual(data["scenes"][0]["visual_direction"], "Zoom on card two")

    def test_unsupported_kind_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "error.json"
            p.write_text(json.dumps({"title": "X", "scenes": [
                {"narration": "Hello.", "kind": "anything_cinematic"}
            ]}))
            with self.assertRaisesRegex(ValueError, "unsupported visual kind"):
                build_from_owner_file(p)

    def test_invalid_language_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "error.json"
            p.write_text(json.dumps({"title": "X", "language": "de",
                                     "scenes": [{"narration": "Hello."}]}))
            with self.assertRaisesRegex(ValueError, "language must"):
                build_from_owner_file(p)

    def test_blank_narration_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "error.json"
            p.write_text(json.dumps({"title": "X", "scenes": [{"narration": " " }]}))
            with self.assertRaisesRegex(ValueError, "nonempty"):
                build_from_owner_file(p)

    def test_missing_chart_labels_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "error.json"
            p.write_text(json.dumps({"title": "X", "scenes": [
                {"narration": "Data.", "kind": "chart"}
            ]}))
            with self.assertRaisesRegex(ValueError, "requires items"):
                build_from_owner_file(p)


if __name__ == "__main__":
    unittest.main()
