import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from four_mode_raw_source_match import compare_bytes

CODE = "202610280101"

class SourceByteMatchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "four_mode_forecasts").mkdir()
        self.title = self.root / "title.csv"
        self.cards = self.root / "cards.csv"
        self.title.write_bytes(b"title example raw bytes")
        self.cards.write_bytes(b"card example raw bytes")
        self.forecast = self.root / "four_mode_forecasts" / (CODE + ".json")
        record = {"schema": "CLEAN_FOUR_MODES_PREDEADLINE_V1", "race_code": CODE,
                  "generated_at_jst": "2026-10-28T10:00:00+09:00",
                  "deadline_jst": "2026-10-28T12:00:00+09:00",
                  "source_sha256": {
                      "title": hashlib.sha256(self.title.read_bytes()).hexdigest(),
                      "race_cards": hashlib.sha256(self.cards.read_bytes()).hexdigest()},
                  "modes": {k: {"tickets": [{"combo":"1-2-3","p":5.0}]} for k in
                            ("hit","balance","hole","narrow")}}
        self.forecast.write_text(json.dumps(record))
    def tearDown(self):
        self.tmp.cleanup()
    def test_matching_bytes_not_formal(self):
        result = compare_bytes(CODE, self.title, self.cards, self.root)
        self.assertEqual(result["status"], "raw_byte_digest_match")
        self.assertFalse(result["remote_first_seen_verified"])
        self.assertFalse(result["formal"])
    def test_changed_bytes_rejected(self):
        self.cards.write_bytes(b"modified data")
        result = compare_bytes(CODE, self.title, self.cards, self.root)
        self.assertEqual(result["status"], "source_digest_mismatch")
        self.assertFalse(result["matching"]["race_cards"])
    def test_missing_bytes_never_claims_match(self):
        self.title.unlink()
        self.assertEqual(compare_bytes(CODE, self.title, self.cards, self.root)["status"],
                         "source_bytes_unavailable_or_invalid")

if __name__ == "__main__":
    unittest.main()
