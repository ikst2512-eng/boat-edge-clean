import json
import subprocess
import threading
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

    def test_invalid_run_timestamp_with_source_links_is_unknown_not_crash(self):
        for stamp in (None, 42, "not-a-timestamp",
                      "2026-11-03T10:00:00", "2026-13-03T10:00:00Z"):
            with self.subTest(created_at=stamp):
                run = {**self.RUN, "created_at": stamp}
                def download(_, root):
                    self.save(root, "four-mode-evidence/source-links.json", {
                        "schema": "FOUR_MODE_LOCAL_SOURCE_LINK_REPORT_V2",
                        "day_jst": "20261103",
                        "publication_scope_status": "publication_scoped",
                        "checked": 2, "hashes_present": 2})
                    self.save(root, "four-mode-evidence/staging.json",
                              {"staged_valid": 2})
                    self.save(root, "four-mode-evidence/stages.json",
                              {"third_rate_ledger": "failure"})
                result = report({"runs": [run]}, download)
                row = result["runs"][0]
                self.assertTrue(row["artifact_present"])
                self.assertIsNone(row["source_link_status"])
                self.assertIsNone(row["source_link_checked"])
                self.assertIsNone(row["source_link_hashes_present"])
                self.assertEqual(row["staged_valid"], 2)
                self.assertEqual(row["third_rate_ledger_outcome"], "failure")

    def test_timezone_aware_run_timestamp_matches_source_link_jst_day(self):
        def download(_, root):
            self.save(root, "four-mode-evidence/source-links.json", {
                "schema": "FOUR_MODE_LOCAL_SOURCE_LINK_REPORT_V2",
                "day_jst": "20261104",
                "publication_scope_status": "publication_scoped",
                "checked": 1, "hashes_present": 1})
        row = report({"runs": [
            {**self.RUN, "created_at": "2026-11-03T15:07:00Z"}]}, download)["runs"][0]
        self.assertEqual(row["source_link_status"], "publication_scoped")
        self.assertEqual(row["source_link_checked"], 1)

    def test_bounded_parallel_downloads_keep_original_run_order(self):
        runs = [
            {"id": 300 + i, "created_at": "2026-11-04T00:07:00Z",
             "capture_conclusion": "success", "failed_steps": []}
            for i in range(4)
        ]
        barrier = threading.Barrier(4, timeout=5)
        def download(run_id, root):
            barrier.wait()
            self.save(root, "four-mode-evidence/staging.json",
                      {"staged_valid": run_id})
        result = report({"runs": runs}, download)
        self.assertEqual(
            [(row["run_id"], row["staged_valid"]) for row in result["runs"]],
            [(300 + i, 300 + i) for i in range(4)])

    def test_morning_nine_scheduled_runs_include_earliest_publication_evidence(self):
        # Chronological GitHub listing is newest first; the first 07:07
        # capture is index 8 by the 09:20 JST daily audit.
        runs = [
            {"id": 900 - i, "created_at": "2026-11-04T00:07:00Z",
             "capture_conclusion": "success", "failed_steps": []}
            for i in range(9)
        ]
        seen = []
        def download(run_id, root):
            seen.append(run_id)
            if run_id == 892:
                self.save(root, "four-mode-evidence/staging.json",
                          {"staged_valid": 3})
                self.save(root, "four-mode-evidence/publication.json",
                          {"outcome": "failed", "stage": "push_main"})
        result = report({"runs": runs}, download)
        self.assertEqual(result["scheduled_runs_checked"], 9)
        self.assertEqual(result["history_runs_omitted"], 0)
        self.assertIn(892, seen)
        self.assertEqual(result["runs"][-1]["staged_valid"], 3)
        self.assertEqual(result["runs"][-1]["failure_stage"], "push_main")

    def test_bounded_coverage_reports_omitted_history_explicitly(self):
        runs = [
            {"id": 1000 + i, "created_at": "2026-11-04T00:07:00Z",
             "capture_conclusion": "success", "failed_steps": []}
            for i in range(15)
        ]
        seen = []
        result = report({"runs": runs}, lambda rid, _: seen.append(rid))
        self.assertEqual(len(seen), 12)
        self.assertEqual(result["history_runs_available"], 15)
        self.assertEqual(result["history_runs_omitted"], 3)
        self.assertFalse(result["remote_main_verified"])

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

    def test_excluded_race_identity_exposed_only_for_matching_run_day(self):
        def download(_, root):
            self.save(root, "four_mode_forecasts/capture_status.json", {
                "day_jst": "20261103",
                "excluded": {"invalid_national_win_rate": 1},
                "excluded_races": [{"race_code": "202611030712",
                                    "reason": "invalid_national_win_rate"}]})
        row = report({"runs": [self.RUN]}, download)["runs"][0]
        self.assertEqual(row["excluded_race_count"], 1)
        self.assertEqual(row["excluded_races"], [
            {"race_code": "202611030712", "reason": "invalid_national_win_rate"}])

    def test_stale_or_malformed_exclusion_identity_never_claimed(self):
        for day, code in (("20261102", "202611020712"),
                          ("20261103", "202611020712"),
                          ("20261103", "invalid")):
            with self.subTest(day=day, code=code):
                def download(_, root):
                    self.save(root, "four_mode_forecasts/capture_status.json", {
                        "day_jst": day, "excluded": {"invalid_national_win_rate": 1},
                        "excluded_races": [{"race_code": code,
                                            "reason": "invalid_national_win_rate"}]})
                row = report({"runs": [self.RUN]}, download)["runs"][0]
                self.assertIsNone(row["excluded_races"])
                if day != "20261103":
                    self.assertIsNone(row["excluded_race_count"])
                else:
                    self.assertEqual(row["excluded_race_count"], 1)

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

    def test_research_roster_matches_exact_same_job_publication(self):
        def download(_, root):
            self.save(root, "four-mode-evidence/publication.json", {
                "outcome": "pushed_to_main", "commit_sha": "a" * 40,
                "added_forecasts": 2})
            codes = ["202611040101", "202611040102"]
            self.save(root, "four-mode-evidence/third-rate-shadow.json", {
                "schema": "V2_THIRD_RATE_SAME_JOB_FROZEN_SHADOW_V1",
                "publication_commit_sha": "a" * 40, "published_forecasts": 2,
                "records": [{"race_code": code} for code in codes]})
            self.save(root, "four-mode-evidence/hole-shadow.json", {
                "schema": "HOLE_SHADOW_PUBLISHED_SAME_JOB_V1",
                "publication_commit_sha": "a" * 40, "published_new_count": 2,
                "records": [{"race_code": code} for code in reversed(codes)]})
        report_data = report({"runs": [self.RUN]}, download)
        self.assertEqual(report_data["runs"][0]["research_roster_evidence"]["status"], "matched")
        self.assertEqual(report_data["research_roster_status_counts"]["matched"], 1)
        self.assertFalse(report_data["remote_main_verified"])
        self.assertEqual(report_data["runs"][0]["research_roster_evidence"]["race_codes"],
                         ["202611040101", "202611040102"])

    def test_partial_hole_freeze_counts_match_records_not_full_success(self):
        def download(_, root):
            self.save(root, "four-mode-evidence/publication.json", {
                "outcome": "pushed_to_main", "commit_sha": "a" * 40,
                "added_forecasts": 2})
            codes = ["202611040101", "202611040102"]
            self.save(root, "four-mode-evidence/third-rate-shadow.json", {
                "schema": "V2_THIRD_RATE_SAME_JOB_FROZEN_SHADOW_V1",
                "publication_commit_sha": "a" * 40, "published_forecasts": 2,
                "frozen_before_t_minus_12": 1, "validation_error_count": 0,
                "records": [{"race_code": codes[0],
                             "status": "frozen_in_same_job_before_t_minus_12"},
                            {"race_code": codes[1], "status": "ineligible"}]})
            self.save(root, "four-mode-evidence/hole-shadow.json", {
                "schema": "HOLE_SHADOW_PUBLISHED_SAME_JOB_V1",
                "publication_commit_sha": "a" * 40, "published_new_count": 2,
                "frozen_count": 1, "validation_error_count": 1,
                "records": [{"race_code": codes[0],
                             "status": "shadow_frozen_unverified"},
                            {"race_code": codes[1], "status": "validation_error"}]})
        result = report({"runs": [self.RUN]}, download)
        self.assertEqual(result["runs"][0]["research_roster_evidence"]["status"], "matched")
        self.assertEqual(result["research_roster_mismatch_run_ids"], [])

    def test_false_hole_freeze_count_is_explicit_research_mismatch(self):
        def download(_, root):
            self.save(root, "four-mode-evidence/publication.json", {
                "outcome": "pushed_to_main", "commit_sha": "a" * 40,
                "added_forecasts": 2})
            codes = ["202611040101", "202611040102"]
            self.save(root, "four-mode-evidence/third-rate-shadow.json", {
                "schema": "V2_THIRD_RATE_SAME_JOB_FROZEN_SHADOW_V1",
                "publication_commit_sha": "a" * 40, "published_forecasts": 2,
                "frozen_before_t_minus_12": 0, "validation_error_count": 0,
                "records": [{"race_code": code, "status": "ineligible"}
                            for code in codes]})
            self.save(root, "four-mode-evidence/hole-shadow.json", {
                "schema": "HOLE_SHADOW_PUBLISHED_SAME_JOB_V1",
                "publication_commit_sha": "a" * 40, "published_new_count": 2,
                "frozen_count": 2, "validation_error_count": 0,
                "records": [{"race_code": codes[0],
                             "status": "shadow_frozen_unverified"},
                            {"race_code": codes[1], "status": "validation_error"}]})
        result = report({"runs": [self.RUN]}, download)
        issue = result["runs"][0]["research_roster_evidence"]
        self.assertEqual(issue["status"], "mismatch")
        self.assertEqual(issue["reason"], "shadow_freeze_accounting_mismatch")
        self.assertEqual(issue["research"], "hole")
        self.assertEqual(issue["field"], "frozen_count")
        self.assertEqual(result["research_roster_mismatch_run_ids"], [123])
        self.assertEqual(result["runs"][0]["publication_outcome"], "pushed_to_main")

    def test_third_rate_ineligible_double_count_detected_independently(self):
        def download(_, root):
            self.save(root, "four-mode-evidence/publication.json", {
                "outcome": "pushed_to_main", "commit_sha": "a" * 40,
                "added_forecasts": 2})
            codes = ["202611040101", "202611040102"]
            self.save(root, "four-mode-evidence/third-rate-shadow.json", {
                "schema": "V2_THIRD_RATE_SAME_JOB_FROZEN_SHADOW_V1",
                "publication_commit_sha": "a" * 40, "published_forecasts": 2,
                "frozen_before_t_minus_12": 1, "ineligible_count": 1,
                "validation_error_count": 1,
                "records": [{"race_code": codes[0],
                             "status": "frozen_in_same_job_before_t_minus_12"},
                            {"race_code": codes[1], "status": "validation_error"}]})
            self.save(root, "four-mode-evidence/hole-shadow.json", {
                "schema": "HOLE_SHADOW_PUBLISHED_SAME_JOB_V1",
                "publication_commit_sha": "a" * 40, "published_new_count": 2,
                "frozen_count": 1, "validation_error_count": 1,
                "records": [{"race_code": codes[0],
                             "status": "shadow_frozen_unverified"},
                            {"race_code": codes[1], "status": "validation_error"}]})
        result = report({"runs": [self.RUN]}, download)
        evidence = result["runs"][0]["research_roster_evidence"]
        self.assertEqual(evidence["status"], "mismatch")
        self.assertEqual(evidence["research"], "third")
        self.assertEqual(evidence["field"], "ineligible_count")
        self.assertEqual(result["research_roster_mismatch_run_ids"], [123])

    def test_research_roster_mismatch_does_not_relabel_push(self):
        def download(_, root):
            self.save(root, "four-mode-evidence/publication.json", {
                "outcome": "pushed_to_main", "commit_sha": "a" * 40,
                "added_forecasts": 1})
            self.save(root, "four-mode-evidence/third-rate-shadow.json", {
                "schema": "V2_THIRD_RATE_SAME_JOB_FROZEN_SHADOW_V1",
                "publication_commit_sha": "a" * 40, "published_forecasts": 1,
                "records": [{"race_code": "202611040101"}]})
            self.save(root, "four-mode-evidence/hole-shadow.json", {
                "schema": "HOLE_SHADOW_PUBLISHED_SAME_JOB_V1",
                "publication_commit_sha": "a" * 40, "published_new_count": 1,
                "records": [{"race_code": "202611040102"}]})
        data = report({"runs": [self.RUN]}, download)
        self.assertEqual(data["research_roster_mismatch_run_ids"], [123])
        self.assertEqual(data["runs"][0]["research_roster_evidence"]["reason"],
                         "shadow_race_rosters_disagree")
        self.assertEqual(data["runs"][0]["publication_outcome"], "pushed_to_main")

    def test_research_roster_absence_is_unknown_not_match(self):
        def download(_, root):
            self.save(root, "four-mode-evidence/publication.json", {
                "outcome": "pushed_to_main", "commit_sha": "a" * 40,
                "added_forecasts": 1})
        data = report({"runs": [self.RUN]}, download)
        self.assertEqual(data["research_roster_status_counts"]["unknown"], 1)
        self.assertEqual(data["research_roster_status_counts"]["matched"], 0)

    def test_server_observation_claims_require_exact_per_race_counts(self):
        race = "202611040101"
        def download(_, root):
            self.save(root, "four-mode-evidence/publication.json", {
                "outcome": "pushed_to_main", "commit_sha": "a" * 40,
                "added_forecasts": 1})
            self.save(root, "four-mode-evidence/github-server-observation.json", {
                "schema": "FOUR_MODE_GITHUB_REMOTE_OBSERVATION_V1",
                "status": "remote_observation_audited_nonformal",
                "publication_commit_sha": "a" * 40, "publication_count": 1,
                "observed_before_t_minus_12": 1,
                "observed_after_t_minus_12": 0, "unverified_count": 0,
                "records": [{"race_code": race, "first_add_commit": "a" * 40,
                             "status": "remote_observation_unverified"}]})
        result = report({"runs": [self.RUN]}, download)
        row = result["runs"][0]
        self.assertEqual(row["github_observation_integrity"]["status"], "mismatch")
        self.assertEqual(row["github_observation_integrity"]["reason"],
                         "observation_count_disagrees_with_rows")
        self.assertIsNone(row["github_observation_before_t12"])
        self.assertEqual(result["github_observation_before_t12_total"], 0)
        self.assertEqual(result["github_observation_integrity_mismatch_run_ids"], [123])

    def test_server_observation_matching_rows_is_not_first_receipt_proof(self):
        def download(_, root):
            self.save(root, "four-mode-evidence/publication.json", {
                "outcome": "pushed_to_main", "commit_sha": "a" * 40,
                "added_forecasts": 1})
            self.save(root, "four-mode-evidence/github-server-observation.json", {
                "schema": "FOUR_MODE_GITHUB_REMOTE_OBSERVATION_V1",
                "status": "remote_observation_audited_nonformal",
                "publication_commit_sha": "a" * 40, "publication_count": 1,
                "observed_before_t_minus_12": 1,
                "observed_after_t_minus_12": 0, "unverified_count": 0,
                "records": [{"race_code": "202611040101",
                             "first_add_commit": "a" * 40,
                             "status": "github_server_observed_before_t_minus_12"}]})
        result = report({"runs": [self.RUN]}, download)
        row = result["runs"][0]
        self.assertEqual(row["github_observation_integrity"]["status"], "matched")
        self.assertEqual(result["github_observation_before_t12_total"], 1)
        self.assertFalse(result["remote_main_verified"])

    def test_remote_server_observation_failure_is_not_hidden_in_successful_capture(self):
        def download(run_id, root):
            self.save(root, "four-mode-evidence/publication.json",
                      {"outcome": "no_eligible_candidates"})
            self.save(root, "four-mode-evidence/stages.json", {
                "github_server_observation": "failure" if run_id == 123 else "success",
                "github_observation_ledger": "failure" if run_id == 123 else "success"})
            self.save(root, "four-mode-evidence/github-server-observation.json", {
                "schema": "FOUR_MODE_GITHUB_REMOTE_OBSERVATION_V1",
                "status": "no_confirmed_publication",
                "observed_before_t_minus_12": 0,
                "observed_after_t_minus_12": 0, "unverified_count": 0})
            self.save(root, "four-mode-evidence/github-server-observation-ledger.json",
                      {"status": "observation_preservation_failed"} if run_id == 123
                       else {"status": "no_published_forecast"})
        result = report({"runs": [self.RUN, {**self.RUN, "id": 124}]}, download)
        self.assertEqual(result["github_observation_coverage"]["failure"], 1)
        self.assertEqual(result["github_observation_ledger_coverage"]["success"], 1)
        self.assertEqual(result["github_observation_failure_run_ids"], [123])
        self.assertEqual(result["github_observation_ledger_failure_run_ids"], [123])
        self.assertIsNone(result["runs"][1]["github_observation_before_t12"])
        self.assertEqual(result["runs"][1]["github_observation_integrity"]["status"],
                         "not_applicable")
        self.assertFalse(result["remote_main_verified"])

    def test_legacy_server_observation_absent_is_unknown(self):
        result = report({"runs": [self.RUN]}, lambda *_: None)
        self.assertEqual(result["github_observation_coverage"]["unknown"], 1)
        self.assertEqual(result["github_observation_ledger_coverage"]["unknown"], 1)
        self.assertEqual(result["github_observation_failure_run_ids"], [])

    def test_ledger_probe_and_failure_are_distinguished_from_capture_success(self):
        def download(run_id, root):
            self.save(root, "four-mode-evidence/publication.json",
                      {"outcome": "no_eligible_candidates"})
            self.save(root, "four-mode-evidence/stages.json",
                      {"third_rate_ledger": "failure" if run_id == 123 else "success"})
            self.save(root, "four-mode-evidence/third-rate-ledger.json",
                      {"status": "ledger_preservation_failed"} if run_id == 123
                       else {"status": "no_eligible_frozen_predictions",
                             "write_access_probe": {
                                 "status": "new_write_permission_probe"}})
        rows = [self.RUN, {**self.RUN, "id": 124}]
        result = report({"runs": rows}, download)
        self.assertEqual(result["third_rate_ledger_failure_run_ids"], [123])
        self.assertEqual(result["third_rate_ledger_probe_verified_run_ids"], [124])
        self.assertEqual(result["third_rate_ledger_coverage"]["success"], 1)
        self.assertEqual(result["third_rate_ledger_coverage"]["failure"], 1)
        self.assertEqual(result["runs"][1]["third_rate_ledger_status"],
                         "no_eligible_frozen_predictions")

    def test_legacy_ledger_absence_stays_unknown(self):
        result = report({"runs": [self.RUN]}, lambda *_: None)
        self.assertEqual(result["third_rate_ledger_coverage"]["unknown"], 1)
        self.assertEqual(result["third_rate_ledger_failure_run_ids"], [])
        self.assertEqual(result["third_rate_ledger_probe_verified_run_ids"], [])

    def test_research_failure_kept_separate_from_verified_push_claim(self):
        def download(_, root):
            self.save(root, "four-mode-evidence/publication.json", {
                "outcome": "pushed_to_main", "added_forecasts": 3,
                "commit_sha": "a" * 40})
            self.save(root, "four-mode-evidence/stages.json", {
                "publication": "pushed_to_main",
                "third_rate_shadow": "failure", "hole_shadow": "success"})
        result = report({"runs": [self.RUN]}, download)
        row = result["runs"][0]
        self.assertEqual(row["publication_outcome"], "pushed_to_main")
        self.assertEqual(row["third_rate_shadow_outcome"], "failure")
        self.assertEqual(row["hole_shadow_outcome"], "success")
        self.assertEqual(result["third_rate_shadow_failure_runs"], [123])
        self.assertEqual(result["hole_shadow_failure_runs"], [])
        self.assertEqual(result["claimed_added_forecasts_sum"], 3)

    def test_legacy_artifacts_are_unknown_not_clean_research(self):
        def download(run_id, root):
            if run_id == 124:
                self.save(root, "four-mode-evidence/stages.json", {
                    "third_rate_shadow": "success", "hole_shadow": "skipped"})
            else:
                self.save(root, "four-mode-evidence/publication.json", {
                    "outcome": "no_eligible_candidates"})
        runs = [self.RUN, {**self.RUN, "id": 124}]
        result = report({"runs": runs}, download)
        self.assertEqual(result["research_stage_coverage"]["third_rate_shadow"],
                         {"success": 1, "failure": 0, "skipped": 0,
                          "cancelled": 0, "unknown": 1, "checked": 2})
        self.assertEqual(result["research_stage_coverage"]["hole_shadow"],
                         {"success": 0, "failure": 0, "skipped": 1,
                          "cancelled": 0, "unknown": 1, "checked": 2})
        self.assertEqual(result["third_rate_shadow_failure_runs"], [])
        self.assertEqual(result["hole_shadow_failure_runs"], [])

    def test_missing_and_invalid_research_verdicts_stay_unknown(self):
        def download(_, root):
            self.save(root, "four-mode-evidence/stages.json", {
                "third_rate_shadow": "unexpected", "hole_shadow": None})
        result = report({"runs": [self.RUN]}, download)
        row = result["runs"][0]
        self.assertIsNone(row["third_rate_shadow_outcome"])
        self.assertIsNone(row["hole_shadow_outcome"])
        self.assertEqual(result["third_rate_shadow_failure_runs"], [])
        self.assertEqual(result["hole_shadow_failure_runs"], [])

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
