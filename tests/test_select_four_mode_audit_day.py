"""Deterministic JST-day selection checks for delayed inventory execution."""
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch

from scripts.select_four_mode_audit_day import main, select_audit_day

JST = timezone(timedelta(hours=9))


class SelectFourModeAuditDayTests(unittest.TestCase):
    def test_delayed_evening_schedule_crosses_midnight(self):
        # Actual failure: 2026-11-08 03:03 JST, before any 11/08 capture.
        self.assertEqual(select_audit_day(
            datetime(2026, 11, 8, 3, 3, tzinfo=JST)), "20261107")

    def test_early_morning_before_first_capture_and_grace(self):
        for hour, minute in [(0, 0), (6, 59), (7, 6), (7, 7), (7, 52), (7, 59)]:
            with self.subTest(hour=hour, minute=minute):
                self.assertEqual(select_audit_day(
                    datetime(2026, 11, 8, hour, minute, tzinfo=JST)), "20261107")

    def test_daily_08_and_09_20_and_22_20_use_current_day(self):
        for hour, minute in [(8, 0), (9, 20), (15, 5), (22, 20), (23, 59)]:
            with self.subTest(hour=hour, minute=minute):
                self.assertEqual(select_audit_day(
                    datetime(2026, 11, 8, hour, minute, tzinfo=JST)), "20261108")

    def test_utc_offset_is_normalized_before_day_selection(self):
        self.assertEqual(select_audit_day(
            datetime(2026, 11, 7, 18, 3, tzinfo=timezone.utc)), "20261107")
        self.assertEqual(select_audit_day(
            datetime(2026, 11, 8, 0, 20, tzinfo=timezone.utc)), "20261108")

    def test_year_boundary(self):
        self.assertEqual(select_audit_day(
            datetime(2027, 1, 1, 4, 0, tzinfo=JST)), "20261231")

    def test_naive_and_non_datetime_rejected(self):
        with self.assertRaises(ValueError):
            select_audit_day(datetime(2026, 11, 8, 3, 3))
        with self.assertRaises(ValueError):
            select_audit_day("2026-11-08")

    def test_selected_day_written_to_github_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "env"
            with patch.dict("os.environ", {"GITHUB_ENV": str(path)}):
                # Time-independent property: the selected value is one JST YYYYMMDD.
                main()
            value = path.read_text(encoding="utf-8")
            self.assertRegex(value, r"\AFOUR_MODE_AUDIT_DAY_JST=20\d{6}\n\Z")

    def test_missing_github_env_fails_instead_of_silent_empty_day(self):
        with patch.dict("os.environ", {"GITHUB_ENV": ""}):
            with self.assertRaises(SystemExit):
                main()


if __name__ == "__main__":
    unittest.main()
