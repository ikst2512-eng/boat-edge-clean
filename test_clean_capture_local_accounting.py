"""Regression checks for local-only CLEAN capture accounting."""
import json
import tempfile
import unittest
from pathlib import Path
from scripts.clean_capture_local_accounting import inspect_log, run

DAY = "20261105"


class CleanCaptureLocalAccountingTests(unittest.TestCase):
    @staticmethod
    def summary(**updates):
        data = {
            "date": DAY, "saved": 7, "eligible": 9,
            "already_frozen": 2, "formal_predictions": 0,
            "scoring_enabled": False,
        }
        data.update(updates)
        return json.dumps(data)

    def test_valid_mixed_log_counts_local_creation_without_remote_claim(self):
        logs = 'PROSPECTIVE_SUPPLEMENT {"eligible": 2}\n' + self.summary()
        r = inspect_log(logs, DAY)
        self.assertEqual((r["eligible_generated"], r["locally_created"],
                          r["already_frozen"]), (9, 7, 2))
        self.assertEqual(r["status"], "local_capture_completed_not_git_proof")
        for flag in ("git_first_add_verified", "remote_first_seen_verified",
                     "formal", "scoring"):
            self.assertIs(r[flag], False)

    def test_all_already_frozen_is_not_a_new_git_addition(self):
        r = inspect_log(self.summary(saved=0, eligible=9, already_frozen=9), DAY)
        self.assertEqual(r["locally_created"], 0)
        self.assertEqual(r["status"], "local_capture_completed_not_git_proof")
        self.assertFalse(r["git_first_add_verified"])

    def test_legitimate_no_eligible_candidates_is_not_a_first_add(self):
        r = inspect_log(self.summary(saved=0, eligible=0, already_frozen=0), DAY)
        self.assertEqual(r["eligible_generated"], 0)
        self.assertFalse(r["git_first_add_verified"])

    def test_missing_log_and_zero_rows_are_not_confirmed(self):
        self.assertEqual(inspect_log(None, DAY)["status"], "capture_log_missing")
        self.assertEqual(inspect_log("  \n", DAY)["status"], "capture_summary_missing")

    def test_exception_stack_trace_is_not_a_success(self):
        content = self.summary() + "\nTraceback: source HTTPError"
        r = inspect_log(content, DAY)
        self.assertEqual(r["status"], "capture_summary_missing")
        self.assertIsNone(r["locally_created"])

    def test_mismatched_day_and_impossible_counts_rejected(self):
        self.assertEqual(inspect_log(self.summary(date="20261104"), DAY)["status"],
                         "capture_day_unverified")
        self.assertEqual(inspect_log(self.summary(saved=11), DAY)["status"],
                         "capture_summary_invalid")
        self.assertEqual(inspect_log(self.summary(saved=-1), DAY)["status"],
                         "capture_summary_invalid")

    def test_boolean_counts_are_not_integers(self):
        self.assertEqual(inspect_log(self.summary(saved=True), DAY)["status"],
                         "capture_summary_invalid")

    def test_no_false_promotion_from_extra_payload_keys(self):
        r = inspect_log(self.summary(formal=True, git_first_add_verified=True,
                                     remote_first_seen_verified=True), DAY)
        self.assertFalse(r["formal"])
        self.assertFalse(r["git_first_add_verified"])
        self.assertFalse(r["remote_first_seen_verified"])

    def test_rogue_formal_or_scoring_flags_fail_closed(self):
        r = inspect_log(self.summary(formal_predictions=1), DAY)
        self.assertEqual(r["status"], "capture_summary_invalid")
        self.assertEqual(inspect_log(self.summary(scoring_enabled=True), DAY)["status"],
                         "capture_summary_invalid")

    def test_missing_log_still_writes_read_only_receipt(self):
        with tempfile.TemporaryDirectory() as d:
            output = Path(d) / "out" / "accounting.json"
            result = run(Path(d) / "missing.log", output, expected_day=DAY)
            self.assertEqual(result["status"], "capture_log_missing")
            self.assertEqual(json.loads(output.read_text()), result)
            self.assertFalse(result["git_first_add_verified"])


if __name__ == "__main__":
    unittest.main()
