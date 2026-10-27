"""Offline regression for the read-only upstream visibility audit."""
import unittest
from unittest.mock import patch
import source_visibility_audit as audit


class AuditTests(unittest.TestCase):
    def test_missing_prediction_and_result_reported_not_raised(self):
        manifest = {"date": "2026-10-27", "updated_at": "2026-10-27T10:00:00+09:00",
                    "venues": [{"jcd": "01", "races": [{"race_no": 1}]}]}
        def fake_get(path):
            return (manifest, None) if path == "today.json" else (None, "HTTP_404")
        with patch.object(audit, "get_json", side_effect=fake_get):
            result = audit.audit("2026-10-27")
        self.assertEqual(result["races"], 1)
        self.assertEqual(result["prediction_missing"], 1)
        self.assertEqual(result["result_missing"], 1)
        self.assertIsNone(result["manifest_error"])

    def test_stale_manifest_blocks_mixed_day(self):
        with patch.object(audit, "get_json", return_value=({"date": "2026-10-26", "venues": []}, None)):
            self.assertEqual(audit.audit("2026-10-27")["manifest_error"], "STALE_MANIFEST_DATE")


if __name__ == "__main__":
    unittest.main()
