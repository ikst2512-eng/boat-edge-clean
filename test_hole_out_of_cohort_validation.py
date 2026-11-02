import tempfile
import unittest
from pathlib import Path
from hole_out_of_cohort_validation import holdout_codes, run

class HoldoutTest(unittest.TestCase):
    def test_never_reuse_training_codes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "four_mode_forecasts").mkdir()
            (root / "confirmed_results").mkdir()
            for code in ("202610310101", "202610310102", "202610310103"):
                (root / "four_mode_forecasts" / (code + ".json")).write_text("{}")
                (root / "confirmed_results" / (code + ".json")).write_text("{}")
            self.assertEqual(holdout_codes(root, ["202610310102"]),
                             ["202610310101", "202610310103"])
    def test_empty_training_is_not_successful_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(run(Path(tmp))["status"], "training_unavailable")
    def test_invalid_limit_and_duplicate_training(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                holdout_codes(Path(tmp), ["202610310101", "202610310101"])
            with self.assertRaises(ValueError):
                holdout_codes(Path(tmp), [], 0)

if __name__ == "__main__":
    unittest.main()
