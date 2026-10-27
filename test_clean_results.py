import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
import clean_results as results


class CleanResultTests(unittest.TestCase):
    def test_missing_result_does_not_fallback(self):
        with tempfile.TemporaryDirectory() as root, patch.object(results, "ROOT", Path(root)), patch.object(results, "urlopen", side_effect=HTTPError("https://example.org", 404, "missing", {}, None)):
            code, obj = results.read_result("20261027", 1, 1)
        self.assertEqual((code, obj["status"]), (404, "not_confirmed"))

    def test_fresh_clean_archive_when_local_deploy_is_old(self):
        record = {"race_code": "202610270101", "status": "confirmed", "finish_order": [1, 2, 3],
                  "source_url": "https://boatracecsv.github.io/data/results/realtime/2026/10/27.csv",
                  "confirmed_at_jst": "2026-10-27T16:00:00+09:00",
                  "collected_at_jst": "2026-10-27T16:01:00+09:00"}
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self, n): return json.dumps(record).encode()
        with tempfile.TemporaryDirectory() as root, patch.object(results, "ROOT", Path(root)), patch.object(results, "urlopen", return_value=Response()) as fetch:
            status, data = results.read_result("20261027", 1, 1)
        self.assertEqual(status, 200)
        self.assertEqual(data["finish_order"], [1, 2, 3])
        self.assertIn("boat-edge-clean/main/confirmed_results/", fetch.call_args.args[0].full_url)

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
