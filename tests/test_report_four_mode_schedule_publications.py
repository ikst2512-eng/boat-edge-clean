import json
import subprocess
import unittest
from pathlib import Path

from scripts.report_four_mode_schedule_publications import inspect, report


class ScheduledEvidenceTest(unittest.TestCase):
    RUN = {"id": 123, "created_at": "2026-11-02T22:07:00Z",
           "capture_conclusion": "success", "failed_steps": []}

    @staticmethod
    def save(root, path, value):
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(value), encoding="utf-8")

    def test_counts_are_read_from_matching_day_and_push_is_only_claimed(self):
        def download(run_id, root):
            self.assertEqual(run_id, 123)
            self.save(root, "four_mode_forecasts/capture_status.json", {
                "day_jst": "20261103", "published_title_rows": 149,
                "published_card_rows": 149, "eligible_forecasts_today": 149,
                "last_run_new_count": 149})
            self.save(root, "four-mode-evidence/staging.json", {"staged_valid": 149})
            self.save(root, "four-mode-evidence/publication.json", {
                "outcome": "pushed_to_main", "added_forecasts": 149,
                "commit_sha": "a" * 40})
        result = report({"runs": [self.RUN]}, download)
        row = result["runs"][0]
        self.assertEqual(row["newly_generated"], 149)
        self.assertEqual(row["staged_valid"], 149)
        self.assertEqual(row["claimed_added_forecasts"], 149)
        self.assertEqual(result["claimed_added_forecasts_sum"], 149)
        self.assertFalse(row["remote_main_verified"])
        self.assertFalse(result["remote_main_verified"])

    def test_stale_capture_status_is_not_counted(self):
        def download(_, root):
            self.save(root, "four_mode_forecasts/capture_status.json", {
                "day_jst": "20261102", "last_run_new_count": 999})
        row = report({"runs": [self.RUN]}, download)["runs"][0]
        self.assertIsNone(row["newly_generated"])

    def test_missing_artifact_not_misreported_as_zero_or_success(self):
        def download(_, root):
            raise subprocess.CalledProcessError(1, ["gh"])
        result = report({"runs": [self.RUN]}, download)
        row = result["runs"][0]
        self.assertFalse(row["artifact_present"])
        self.assertIsNone(row["claimed_added_forecasts"])
        self.assertEqual(row["artifact_download_error"], "CalledProcessError")
        self.assertIsNone(result["claimed_added_forecasts_sum"])

    def test_failed_publication_records_stage(self):
        def download(_, root):
            self.save(root, "four-mode-evidence/staging.json", {"staged_valid": 0})
            self.save(root, "four-mode-evidence/publication.json", {
                "outcome": "failed", "stage": "push_main", "exit_code": 1})
        row = report({"runs": [self.RUN]}, download)["runs"][0]
        self.assertEqual(row["failure_stage"], "push_main")
        self.assertEqual(row["staged_valid"], 0)
        self.assertIsNone(row["claimed_added_forecasts"])

    def test_reject_negative_counts_and_invalid_commit_sha(self):
        def download(_, root):
            self.save(root, "four-mode-evidence/publication.json", {
                "outcome": "pushed_to_main", "added_forecasts": -1,
                "commit_sha": "invalid"})
        row = report({"runs": [self.RUN]}, download)["runs"][0]
        self.assertIsNone(row["claimed_added_forecasts"])
        self.assertIsNone(row["claimed_commit_sha"])

    def test_reject_bad_run_and_history(self):
        with self.assertRaises(ValueError):
            report({"runs": [{"id": True}]}, lambda *_: None)
        with self.assertRaises(ValueError):
            report({"runs": []}, lambda *_: None, limit=0)

    def test_new_noop_link_report_counts_zero_not_old_149(self):
        def download(_, root):
            self.save(root, "four-mode-evidence/source-links.json", {
                "schema": "FOUR_MODE_LOCAL_SOURCE_LINK_REPORT_V2",
                "day_jst": "20261103",
                "publication_scope_status": "no_new_publication",
                "checked": 0, "hashes_present": 0, "formal": False})
        row = report({"runs": [self.RUN]}, download)["runs"][0]
        self.assertEqual(row["source_link_status"], "no_new_publication")
        self.assertEqual(row["source_link_checked"], 0)
        self.assertEqual(row["source_link_hashes_present"], 0)
        self.assertFalse(row["source_link_formal"])

    def test_legacy_all_day_hash_count_is_flagged_not_current_job_failure(self):
        def download(_, root):
            self.save(root, "four-mode-evidence/source-links.json", {
                "schema": "FOUR_MODE_LOCAL_SOURCE_LINK_REPORT_V1",
                "day_jst": "20261103",
                "checked": 149, "hashes_present": 0})
        row = report({"runs": [self.RUN]}, download)["runs"][0]
        self.assertEqual(row["source_link_status"], "legacy_all_day_archives")
        self.assertEqual(row["source_link_checked"], 149)

    def test_wrong_day_link_report_does_not_count(self):
        def download(_, root):
            self.save(root, "four-mode-evidence/source-links.json", {
                "schema": "FOUR_MODE_LOCAL_SOURCE_LINK_REPORT_V2",
                "day_jst": "20261102", "checked": 999, "hashes_present": 0})
        row = report({"runs": [self.RUN]}, download)["runs"][0]
        self.assertIsNone(row["source_link_checked"])


if __name__ == "__main__":
    unittest.main()
