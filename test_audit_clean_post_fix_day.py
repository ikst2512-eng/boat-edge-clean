"""Read-only daily post-fix diagnostics. Never promote local Git evidence to formal."""
import json
import tempfile
import unittest
from pathlib import Path

from audit_clean_post_fix_cohort import inspect_post_fix, post_fix_paths


class DailyPostFixIsolationTests(unittest.TestCase):
    def test_scheduled_backup_also_archives_jst_day_without_hiding_global_failure(self):
        wf=(Path(__file__).resolve().parent /
            ".github/workflows/clean-prospective-evaluation.yml").read_text()
        self.assertIn("python audit_clean_post_fix_cohort.py > test-results/post-fix-first-add.json", wf)
        self.assertIn('python audit_clean_post_fix_cohort.py --day "$day" > test-results/post-fix-first-add-day.json', wf)
        self.assertIn("day=$(TZ=Asia/Tokyo date +%Y%m%d)", wf)
        self.assertIn("if: always()", wf)
        self.assertIn("data['formal'] is not False", wf)
        self.assertIn("data['remote_first_seen_verified'] is not False", wf)
        self.assertIn("test-results/post-fix-first-add-day.json", wf)
        self.assertIn("  schedule:", wf)
        self.assertIn("    - cron: '30 3,12 * * *'", wf)
        self.assertIn("    - name: Audit existing immutable candidate commits if present", wf)

    def test_nov5_failure_cannot_mask_nov6_local_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp) / "prospective_predictions"
            directory.mkdir()
            for code in ("202611050101", "202611060101", "202611060102"):
                (directory / (code + ".json")).write_text(json.dumps({"race_code": code}))
            calls = []
            def isolated_auditor(paths, root):
                calls.append(list(paths))
                return {
                    "total": len(paths), "local_audit_passed": len(paths),
                    "rejected": 0, "rejection_reasons": {},
                    "by_day": {"20261106": {"total": len(paths)}},
                }
            result = inspect_post_fix(root=tmp, auditor=isolated_auditor, day="20261106")
            self.assertEqual(result["day_jst"], "20261106")
            self.assertEqual(result["candidate_count"], 2)
            self.assertEqual(result["status"], "local_first_add_passed")
            self.assertEqual(calls, [[
                "prospective_predictions/202611060101.json",
                "prospective_predictions/202611060102.json",
            ]])
            self.assertFalse(result["formal"])
            self.assertFalse(result["remote_first_seen_verified"])
            self.assertEqual(len(post_fix_paths(tmp)), 3)

    def test_missing_day_is_pending_not_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp) / "prospective_predictions"
            directory.mkdir()
            (directory / "202611050101.json").write_text("{}")
            result = inspect_post_fix(root=tmp, day="20261106")
            self.assertEqual(result["status"], "pending_no_new_capture")
            self.assertEqual(result["candidate_count"], 0)
            self.assertEqual(result["local_audit_passed"], 0)
            self.assertFalse(result["formal"])
            self.assertFalse(result["remote_first_seen_verified"])

    def test_day_rejected_cohort_still_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp) / "prospective_predictions"
            directory.mkdir()
            (directory / "202611050101.json").write_text("{}")
            def reject(paths, root):
                return {
                    "total": len(paths), "local_audit_passed": 0, "rejected": len(paths),
                    "rejection_reasons": {"first_commit_same_second_unverified": len(paths)},
                    "by_day": {"20261105": {"total": len(paths)}},
                }
            result = inspect_post_fix(root=tmp, auditor=reject, day="20261105")
            self.assertEqual(result["status"], "post_fix_evidence_rejected")
            self.assertEqual(result["rejected"], 1)
            self.assertFalse(result["formal"])

    def test_independent_day_does_not_include_later_dates(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp) / "prospective_predictions"
            directory.mkdir()
            for code in ("202611050101", "202611060101", "202611070101"):
                (directory / (code + ".json")).write_text("{}")
            self.assertEqual(post_fix_paths(tmp, day="20261106"),
                             ["prospective_predictions/202611060101.json"])
            self.assertEqual(post_fix_paths(tmp, day="20261107"),
                             ["prospective_predictions/202611070101.json"])
            self.assertEqual(len(post_fix_paths(tmp)), 3)

    def test_invalid_or_earlier_days_fail_closed(self):
        for day in ("20261104", "20261131", "20261306", "2026116",
                    "2026-11-06", "xyz", "", 20261106, True):
            with self.subTest(day=day), self.assertRaises(ValueError):
                post_fix_paths(day=day)


if __name__ == "__main__":
    unittest.main()
