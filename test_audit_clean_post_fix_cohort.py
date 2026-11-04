import tempfile
import unittest
from pathlib import Path
from audit_clean_post_fix_cohort import POST_FIX_START, inspect_post_fix, post_fix_paths


class PostFixCohortTests(unittest.TestCase):
    def test_no_new_capture_is_pending_not_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = inspect_post_fix(Path(tmp))
        self.assertEqual(result["status"], "pending_no_new_capture")
        self.assertEqual(result["candidate_count"], 0)
        self.assertFalse(result["remote_first_seen_verified"])
        self.assertFalse(result["formal"])

    def test_filters_legacy_and_malformed_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / "prospective_predictions"
            d.mkdir()
            for name in (
                "202611040404.json",
                "202611050404.json",
                "202611060101.json",
                "notes.json",
                "2026110504.json",
            ):
                (d / name).write_text("{}")
            self.assertEqual(post_fix_paths(Path(tmp)), [
                "prospective_predictions/202611050404.json",
                "prospective_predictions/202611060101.json",
            ])
        self.assertEqual(POST_FIX_START, "20261105")

    def test_valid_new_records_remain_research_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / "prospective_predictions"
            d.mkdir()
            (d / "202611050404.json").write_text("{}")
            calls = []
            def passing(paths, root):
                calls.append(paths)
                return {"total": 1, "local_audit_passed": 1, "rejected": 0,
                        "local_passed_records": [{"race_code": "202611050404"}],
                        "rejected_records": []}
            result = inspect_post_fix(Path(tmp), passing)
        self.assertEqual(calls, [["prospective_predictions/202611050404.json"]])
        self.assertEqual(result["status"], "local_first_add_passed")
        self.assertFalse(result["remote_first_seen_verified"])
        self.assertFalse(result["formal"])

    def test_mixed_new_records_are_rejected_not_averaged(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / "prospective_predictions"
            d.mkdir()
            for name in ("202611050404.json", "202611050405.json"):
                (d / name).write_text("{}")
            def mixed(paths, root):
                self.assertEqual(len(paths), 2)
                return {"total": 2, "local_audit_passed": 1, "rejected": 1,
                        "rejected_records": [{"race_code": "202611050405"}]}
            result = inspect_post_fix(Path(tmp), mixed)
        self.assertEqual(result["status"], "post_fix_evidence_rejected")
        self.assertEqual(result["local_audit_passed"], 1)
        self.assertEqual(result["rejected"], 1)


if __name__ == "__main__":
    unittest.main()
