import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from hole_shadow_push_capture import added_forecast_codes, capture

BEFORE = "a" * 40
AFTER = "b" * 40

class PushCaptureTest(unittest.TestCase):
    def test_only_added_valid_forecasts(self):
        codes = added_forecast_codes(BEFORE, AFTER, "four_mode_forecasts/202611030101.json\n"
            "four_mode_forecasts/202611030101.json\n"
            "confirmed_results/202611030102.json\n"
            "four_mode_forecasts/nope.json\n")
        self.assertEqual(codes, ["202611030101"])

    def test_invalid_sha_and_first_push_rejected(self):
        with self.assertRaises(ValueError):
            added_forecast_codes("main", AFTER, "")
        with self.assertRaises(ValueError):
            added_forecast_codes("0" * 40, AFTER, "")

    def test_capture_keeps_unverified_and_does_not_read_results(self):
        with tempfile.TemporaryDirectory() as tmp:
            now = datetime(2026, 11, 3, 6, tzinfo=timezone.utc)
            with patch("hole_shadow_push_capture.freeze", return_value={
                    "status": "shadow_frozen_unverified", "prospective_verified": False}) as mock_freeze:
                report = capture(Path(tmp), BEFORE, AFTER, "123", now,
                                 "four_mode_forecasts/202611030101.json\n")
            self.assertEqual(report["frozen_count"], 1)
            self.assertFalse(report["prospective_verified"])
            self.assertFalse(report["formal"])
            mock_freeze.assert_called_once()

    def test_no_added_archives_does_not_imply_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = capture(Path(tmp), BEFORE, AFTER, "123",
                             datetime.now(timezone.utc), "")
            self.assertEqual(report["frozen_count"], 0)
            self.assertEqual(report["new_forecast_files"], 0)

if __name__ == "__main__":
    unittest.main()
