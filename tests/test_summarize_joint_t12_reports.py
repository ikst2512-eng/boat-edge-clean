import json
import tempfile
import unittest
from pathlib import Path
from scripts.summarize_joint_t12_reports import summarize


class T12SummaryTests(unittest.TestCase):
    def test_counts_only_existing_observed_attempts(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            samples = [
                ("joint_1.json", {"race_code":"202611031501","attempt":1,"both_complete_before_t12":False,"failure_category":"transport"}),
                ("joint_2.json", {"race_code":"202611031501","attempt":2,"both_complete_before_t12":True}),
                ("joint_3.json", {"race_code":"202611031502","attempt":1,"both_complete_before_t12":False,"status":"beforeinfo_after_t12"}),
            ]
            for name, doc in samples:
                (root/name).write_text(json.dumps(doc))
            result = summarize(root)
            self.assertEqual(result["valid_attempt_reports"], 3)
            self.assertEqual(result["distinct_races_in_reports"], 2)
            self.assertEqual(result["complete_pair_attempts"], 1)
            self.assertEqual(result["category_counts"], {"complete_pair":1,"cutoff":1,"transport":1})
            self.assertIsNone(result["historical_success_rate"])
            self.assertFalse(result["forecast_usable"])

    def test_malformed_and_duplicate_reports_never_count_as_success(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root/"joint_1.json").write_text("{not json")
            for name in ("joint_2.json","joint_3.json"):
                (root/name).write_text(json.dumps({"race_code":"202611031501","attempt":2,"both_complete_before_t12":True}))
            result = summarize(root)
            self.assertEqual(result["valid_attempt_reports"], 1)
            self.assertEqual(result["invalid_or_duplicate_reports"], 2)
            self.assertEqual(result["complete_pair_attempts"], 1)

    def test_no_reports_is_not_zero_historical_success_rate(self):
        with tempfile.TemporaryDirectory() as d:
            result = summarize(d)
            self.assertEqual(result["report_files"], 0)
            self.assertIsNone(result["historical_success_rate"])


if __name__ == "__main__":
    unittest.main()
