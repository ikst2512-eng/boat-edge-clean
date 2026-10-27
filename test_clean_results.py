import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import clean_results as results


class CleanResultTests(unittest.TestCase):
    def test_missing_result_does_not_fallback(self):
        with tempfile.TemporaryDirectory() as root, patch.object(results, "ROOT", Path(root)):
            code, obj = results.read_result("20261027", 1, 1)
        self.assertEqual((code, obj["status"]), (404, "not_confirmed"))

    def test_provenance_required(self):
        with tempfile.TemporaryDirectory() as root, patch.object(results, "ROOT", Path(root)):
            store = Path(root) / "confirmed_results"
            store.mkdir()
            path = store / "202610270101.json"
            valid = {"race_code":"202610270101","status":"confirmed","finish_order":[1,2,3],
                     "source_url":"https://example.org/official/202610270101",
                     "confirmed_at_jst":"2026-10-27T16:00:00+09:00",
                     "collected_at_jst":"2026-10-27T16:01:00+09:00"}
            path.write_text(json.dumps(valid), encoding="utf-8")
            self.assertEqual(results.read_result("20261027", 1, 1)[0], 200)
            del valid["source_url"]
            path.write_text(json.dumps(valid), encoding="utf-8")
            self.assertEqual(results.read_result("20261027", 1, 1)[0], 503)

    def test_invalid_race(self):
        self.assertEqual(results.read_result("20261027", 99, 1)[0], 400)


if __name__ == "__main__":
    unittest.main()
