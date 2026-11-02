import unittest
from datetime import datetime
from scripts.backfill_clean_result_day import validate_day, run
from collect_clean_results import JST

NOW = datetime(2026, 11, 3, 9, 0, tzinfo=JST)

class BackfillDayTests(unittest.TestCase):
    def test_allowed_past_days(self):
        for day in ("20261028", "20261031", "20261102"):
            self.assertEqual(validate_day(day, NOW), day)

    def test_rejects_future_today_old_malformed(self):
        for day in ("20261103", "20261104", "20260901", "20260230", "2026-10-28", "", "2026102a"):
            with self.subTest(day=day), self.assertRaises(ValueError):
                validate_day(day, NOW)

    def test_collector_only_receives_validated_day(self):
        seen = []
        report = run("20261028", NOW, lambda day: seen.append(day) or {"day": day, "saved": 0})
        self.assertEqual(seen, ["20261028"])
        self.assertFalse(report["forecast_modified"])
        self.assertFalse(report["formal_accuracy_proven"])

    def test_bad_input_does_not_call_collector(self):
        seen = []
        with self.assertRaises(ValueError):
            run("20261104", NOW, lambda day: seen.append(day))
        self.assertEqual(seen, [])

if __name__ == "__main__":
    unittest.main()
