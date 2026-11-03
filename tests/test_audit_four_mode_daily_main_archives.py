import json
import tempfile
import unittest
from pathlib import Path
from scripts.audit_four_mode_daily_main_archives import audit, parse_additions, scheduled_audit_alert, positive_eligible_run_ids, inspect_day_archive_versions, inspect_first_add_commit_days, reconcile_claimed_pushes

A = "a" * 40
B = "b" * 40
P = "four_mode_forecasts/202611040101.json"
P2 = "four_mode_forecasts/202611040102.json"
OLD = "four_mode_forecasts/202611030101.json"


class DailyMainArchivesTest(unittest.TestCase):
    def test_claimed_push_matches_actual_first_add_commit_and_count(self):
        row = {"run_id": 415, "created_at": "2026-11-04T00:07:00Z",
               "artifact_present": True, "publication_outcome": "pushed_to_main",
               "claimed_commit_sha": A, "claimed_added_forecasts": 2}
        checked, missing = reconcile_claimed_pushes(
            "20261104", [P, P2, OLD], {P: [A], P2: [A]}, [{"runs": [row]}])
        self.assertEqual(len(checked), 1)
        self.assertEqual(checked[0]["first_add_archives_in_checkout"], 2)
        self.assertEqual(missing, [])

    def test_claimed_push_cannot_hide_partial_or_absent_archive(self):
        row = {"run_id": 415, "created_at": "2026-11-04T00:07:00Z",
               "artifact_present": True, "publication_outcome": "pushed_to_main",
               "claimed_commit_sha": A, "claimed_added_forecasts": 2}
        checked, missing = reconcile_claimed_pushes(
            "20261104", [P, OLD], {P: [A]}, [{"runs": [row]}])
        self.assertEqual(checked, [])
        self.assertEqual(missing[0]["first_add_archives_in_checkout"], 1)
        row["claimed_commit_sha"] = B
        _, missing = reconcile_claimed_pushes(
            "20261104", [P, OLD], {P: [A]}, [{"runs": [row]}])
        self.assertEqual(missing[0]["first_add_archives_in_checkout"], 0)

    def test_claimed_push_does_not_mix_prior_day_or_noop_runs(self):
        report = {"runs": [
            {"run_id": 10, "created_at": "2026-11-03T14:00:00Z",
             "artifact_present": True, "publication_outcome": "pushed_to_main",
             "claimed_commit_sha": A, "claimed_added_forecasts": 1},
            {"run_id": 11, "created_at": "2026-11-04T00:07:00Z",
             "artifact_present": True, "publication_outcome": "no_eligible_candidates"}]}
        checked, missing = reconcile_claimed_pushes(
            "20261104", [P], {P: [A]}, [report])
        self.assertEqual((checked, missing), ([], []))

    def test_schedule_fails_closed_on_wrong_or_unknown_first_add_day(self):
        script = Path("scripts/audit_four_mode_daily_main_archives.py").read_text(
            encoding="utf-8")
        self.assertIn(
            'and not report["same_day_git_commit_time_verified"]',
            script,
        )
        self.assertIn(
            "Daily V2 archive first-add Git commit dates are mismatched or unknown",
            script,
        )
        self.assertLess(
            script.index('and not report["same_day_git_commit_time_verified"]'),
            script.index('and not report["v2_archive_payloads_verified"]'),
        )

    def test_archive_commit_jst_day_separate_from_filename_day(self):
        paths = [P, P2, OLD]
        commits = {A: "2026-11-03T15:05:00+00:00",
                   B: "2026-11-03T14:55:00+00:00"}
        result, late = inspect_first_add_commit_days(
            "20261104", {P: [A], P2: [B]}, paths, lambda sha: commits[sha])
        self.assertEqual(result, {"same_day": 1, "other_day": 1, "unknown": 0})
        self.assertEqual(late, [P2])

    def test_malformed_or_missing_commit_date_is_unknown(self):
        paths = [P, P2]
        result, late = inspect_first_add_commit_days(
            "20261104", {P: [A], P2: []}, paths, lambda sha: "invalid timestamp")
        self.assertEqual(result, {"same_day": 0, "other_day": 0, "unknown": 2})
        self.assertEqual(late, [])

    def test_main_archive_audit_runs_independently_of_liveness_failure(self):
        workflow = Path(".github/workflows/four-mode-schedule-inventory.yml").read_text(
            encoding="utf-8")
        self.assertIn(
            "name: Confirm today's first-add archive presence in checked-out Git main" + chr(10)
            + "        if: always()" + chr(10),
            workflow,
        )
        self.assertIn(
            "name: Audit today's actual capture execution separately from Git archives" + chr(10)
            + "        if: always()" + chr(10),
            workflow,
        )

    def test_november_fourth_first_add_proven_only_as_git_evidence(self):
        adds = parse_additions(A + "\n\n" + P + "\n" + P2 + "\n\n" + B + "\n\n" + OLD + "\n")
        result = audit("20261104", [P, P2, OLD, "four_mode_forecasts/capture_status.json"],
                       adds, main_context=True)
        self.assertEqual(result["today_archive_count"], 2)
        self.assertEqual(result["today_single_first_add_count"], 2)
        self.assertTrue(result["main_git_addition_evidence_present"])
        self.assertEqual(result["assessment"], "new_day_git_archives_found")
        self.assertFalse(result["independent_remote_first_seen_verified"])
        self.assertFalse(result["source_predeadline_verified"])

    def test_day_archive_payload_versions_are_counted_separately(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "four_mode_forecasts").mkdir()
            (root / P).write_text(json.dumps({"model_version": "CLEAN_FOUR_MODES_V2_PROVISIONAL_UNCALIBRATED"}))
            (root / P2).write_text(json.dumps({"model_version": "CLEAN_FOUR_MODES_V1_UNCALIBRATED"}))
            bad = "four_mode_forecasts/202611040103.json"
            (root / bad).write_text("{invalid")
            counts, invalid = inspect_day_archive_versions("20261104", [P, P2, bad, OLD], root)
            self.assertEqual(counts, {"v2": 1, "other_model": 1, "invalid": 1})
            self.assertEqual(invalid, [bad])

    def test_all_v2_archives_accepted_as_content_only(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "four_mode_forecasts").mkdir()
            for name in [P, P2]:
                (root / name).write_text(json.dumps({"model_version": "CLEAN_FOUR_MODES_V2_PROVISIONAL_UNCALIBRATED"}))
            counts, invalid = inspect_day_archive_versions("20261104", [P, P2, OLD], root)
            self.assertEqual(counts["v2"], 2)
            self.assertEqual(invalid, [])

    def test_capture_status_metadata_is_not_an_archive(self):
        raw = A + "\n\n" + "four_mode_forecasts/capture_status.json" + "\n" + P + "\n"
        adds = parse_additions(raw)
        self.assertEqual(adds, {P: [A]})

    def test_no_new_day_is_pending_not_success(self):
        result = audit("20261104", [OLD], {OLD: [A]}, main_context=True)
        self.assertEqual(result["today_archive_count"], 0)
        self.assertEqual(result["assessment"], "no_new_day_archives_yet")
        self.assertFalse(result["main_git_addition_evidence_present"])

    def test_missing_or_readded_archive_not_proven(self):
        result = audit("20261104", [P, P2], {P: [A, B]}, main_context=True)
        self.assertEqual(result["assessment"], "git_first_add_incomplete")
        self.assertEqual(result["today_multiple_first_add_count"], 1)
        self.assertEqual(result["today_missing_first_add_count"], 1)

    def test_pr_checkout_cannot_claim_main(self):
        result = audit("20261104", [P], {P: [A]}, main_context=False)
        self.assertEqual(result["assessment"], "not_main_checkout")
        self.assertFalse(result["main_git_addition_evidence_present"])

    def test_daily_cron_alerts_on_absence_without_affecting_pr_or_push(self):
        missing = audit("20261104", [OLD], {OLD: [A]}, main_context=True)
        self.assertFalse(scheduled_audit_alert(missing, "schedule"))
        self.assertTrue(scheduled_audit_alert(missing, "schedule", [self.positive_capture()]))
        self.assertFalse(scheduled_audit_alert(missing, "push"))
        self.assertFalse(scheduled_audit_alert(missing, "pull_request"))
        pr = audit("20261104", [OLD], {OLD: [A]}, main_context=False)
        self.assertFalse(scheduled_audit_alert(pr, "schedule"))

    def test_daily_cron_alerts_on_incomplete_first_add_only(self):
        bad = audit("20261104", [P], {}, main_context=True)
        good = audit("20261104", [P], {P: [A]}, main_context=True)
        self.assertTrue(scheduled_audit_alert(bad, "schedule"))
        self.assertFalse(scheduled_audit_alert(good, "schedule"))


    @staticmethod
    def positive_capture(at="2026-11-04T00:07:00Z", eligible=3, present=True):
        return {"runs": [{"run_id": 415, "created_at": at,
                          "artifact_present": present, "generated_today": 0, "newly_generated": eligible}]}

    def test_cross_day_or_missing_artifact_not_positive(self):
        missing = audit("20261104", [OLD], {OLD: [A]}, main_context=True)
        self.assertFalse(scheduled_audit_alert(missing, "schedule",
                                               [self.positive_capture("2026-11-03T14:00:00Z")]))
        self.assertFalse(scheduled_audit_alert(missing, "schedule",
                                               [self.positive_capture(present=False)]))
        self.assertFalse(scheduled_audit_alert(missing, "schedule",
                                               [self.positive_capture(eligible=0)]))
        self.assertEqual(positive_eligible_run_ids("20261104", [self.positive_capture()]), [415])

    def test_existing_local_archives_do_not_prove_new_candidates(self):
        missing = audit("20261104", [OLD], {OLD: [A]}, main_context=True)
        record = self.positive_capture(eligible=0)
        record["runs"][0]["generated_today"] = 149
        self.assertFalse(scheduled_audit_alert(missing, "schedule", [record]))
        self.assertEqual(positive_eligible_run_ids("20261104", [record]), [])

    def test_staged_valid_and_claimed_push_are_positive(self):
        for key in ("staged_valid", "claimed_added_forecasts"):
            report = self.positive_capture(eligible=0)
            report["runs"][0][key] = 2
            self.assertEqual(positive_eligible_run_ids("20261104", [report]), [415])

    def test_positive_same_day_from_dispatch_evidence(self):
        missing = audit("20261104", [OLD], {OLD: [A]}, main_context=True)
        report = {"schema": "FOUR_MODE_DISPATCH_PUBLICATION_EVIDENCE_V1", **self.positive_capture()}
        self.assertTrue(scheduled_audit_alert(missing, "schedule", [report]))
        self.assertFalse(scheduled_audit_alert(missing, "push", [report]))

    def test_reject_malformed_history_and_tree(self):
        with self.assertRaises(ValueError):
            parse_additions(P)
        with self.assertRaises(ValueError):
            audit("20261104", [P, P], {}, main_context=True)
        with self.assertRaises(ValueError):
            audit("2026-11-04", [], {}, main_context=True)
        with self.assertRaises(ValueError):
            audit("20261104", [123], {}, main_context=True)


if __name__ == "__main__":
    unittest.main()
