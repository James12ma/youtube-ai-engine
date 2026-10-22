"""Film orders from Telegram: the script is fetched privately and must match the owner's hash."""
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path

from studio.order import read_order

SCRIPT = "At two a.m., Maya finally finds the job she wants."


class OrderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cwd = os.getcwd()
        os.chdir(self.tmp.name)
        os.environ["TELEGRAM_BOT_TOKEN"] = "TEST_ONLY"

    def tearDown(self):
        os.chdir(self.cwd)
        self.tmp.cleanup()

    def order(self, **kw):
        p = Path("o.json")
        p.write_text(json.dumps({"id": "F1a2", **kw}))
        return p

    def test_telegram_order_writes_verified_script(self):
        doc = json.dumps({"script": SCRIPT, "language": "es", "voice": "ef_dora", "title": "T"}).encode()
        out = read_order(self.order(telegram_file_id="X", source_sha256=hashlib.sha256(SCRIPT.encode()).hexdigest()),
                         fetch=lambda fid, tok: doc)
        self.assertEqual((out["id"], out["lang"], out["voice"]), ("f1a2", "es", "ef_dora"))
        self.assertEqual(Path(out["film"], "script.txt").read_text().strip(), SCRIPT)

    def test_hash_mismatch_refuses(self):
        doc = json.dumps({"script": SCRIPT + " tampered"}).encode()
        with self.assertRaises(SystemExit):
            read_order(self.order(telegram_file_id="X", source_sha256=hashlib.sha256(SCRIPT.encode()).hexdigest()),
                       fetch=lambda fid, tok: doc)

    def test_existing_film_folder_order(self):
        out = read_order(self.order(film="studio/films/gate_a"))
        self.assertEqual(out["film"], "studio/films/gate_a")

    def test_path_escape_rejected(self):
        with self.assertRaises(SystemExit):
            read_order(self.order(film="../../etc"))


if __name__ == "__main__":
    unittest.main()
