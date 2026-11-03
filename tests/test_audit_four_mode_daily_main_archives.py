import json
import tempfile
import unittest
from pathlib import Path
from scripts.audit_four_mode_daily_main_archives import audit, parse_additions, scheduled_audit_alert, positive_eligible_run_ids, inspect_day_archive_versions, inspect_first_add_commit_days, reconcile_claimed_pushes, unpublished_new_candidate_runs, reconcile_research_rosters_with_main, ledger_failure_run_ids, github_observation_failure_run_ids, final_evidence_failure_run_ids, missing_new_push_final_evidence_run_ids, uncertified_new_push_final_evidence_run_ids, research_shadow_failure_run_ids

A = "a" * 40
B = "b" * 40
P = "four_mode_forecasts/202611040101.json"
P2 = "four_mode_forecasts/202611040102.json"
OLD = "four_mode_forecasts/202611030101.json"


class DailyMainArchivesTest(unittest.TestCase):
    def test_research_shadow_stage_failures_are_day_scoped_and_deduplicated(self):
        third = {"run_id": 1001, "created_at": "2026-11-03T15:07:00Z",
                 "third_rate_shadow_outcome": "failure", "hole_shadow_outcome": "success"}
        hole = {"run_id": 1002, "created_at": "2026-11-04T09:07:00+09:00",
                "third_rate_shadow_outcome": "success", "hole_shadow_outcome": "failure"}
        old = {"run_id": 1003, "created_at": "2026-11-03T14:59:00Z",
               "third_rate_shadow_outcome": "failure", "hole_shadow_outcome": "failure"}
        missing = {"run_id": 1004, "created_at": "2026-11-04T09:22:00+09:00"}
        evidence = [{"runs": [third, hole, old, missing]},
                    {"runs": [dict(third)]}]
        self.assertEqual(research_shadow_failure_run_ids("20261104", evidence),
                         {"third_rate_shadow": [1001], "hole_shadow": [1002]})
        self.assertEqual(research_shadow_failure_run_ids("20261105", evidence),
                         {"third_rate_shadow": [], "hole_shadow": []})
        source = Path("scripts/audit_four_mode_daily_main_archives.py").read_text(
            encoding="utf-8")
        self.assertIn('any(report["research_shadow_failure_run_ids"].values())', source)

    def test_unknown_or_malformed_research_stage_evidence_not_fabricated_failure(self):
        evidence = {"runs": [
            {"run_id": 1005, "created_at": "bad", "third_rate_shadow_outcome": "failure"},
            {"run_id": 1006, "created_at": "2026-11-04T09:07:00",
             "hole_shadow_outcome": "failure"},
            {"run_id": 1007, "created_at": "2026-11-04T09:07:00+09:00",
             "third_rate_shadow_outcome": None, "hole_shadow_outcome": "skipped"},
        ]}
        self.assertEqual(research_shadow_failure_run_ids("20261104", [evidence]),
                         {"third_rate_shadow": [], "hole_shadow": []})

    def test_final_gate_passed_label_without_matching_published_detail_fails(self):
        base = {
            "run_id": 951, "created_at": "2026-11-03T15:07:00Z",
            "artifact_present": True, "publication_outcome": "pushed_to_main",
            "claimed_added_forecasts": 2,
            "final_evidence_verdict_status": "passed",
            "final_evidence_verdict_result": "published_with_durable_early_observation",
            "final_evidence_published_count": 2,
        }
        good = dict(base)
        wrong_count = {**base, "run_id": 952,
                       "final_evidence_published_count": 1}
        mislabeled_noop = {**base, "run_id": 953,
                           "final_evidence_verdict_result": "no_new_forecasts"}
        missing_detail = {**base, "run_id": 954,
                          "final_evidence_verdict_result": None}
        failed = {**base, "run_id": 955, "final_evidence_verdict_status": "failed"}
        no_op = {**base, "run_id": 956,
                 "publication_outcome": "no_eligible_candidates"}
        old = {**wrong_count, "run_id": 957,
               "created_at": "2026-11-03T14:59:00Z"}
        report = {"runs": [good, wrong_count, mislabeled_noop,
                           missing_detail, failed, no_op, old]}
        self.assertEqual(uncertified_new_push_final_evidence_run_ids(
            "20261104", [report, {"runs": [dict(wrong_count)]}]),
            [952, 953, 954])
        self.assertEqual(uncertified_new_push_final_evidence_run_ids(
            "20261103", [report]), [])
        script = Path("scripts/audit_four_mode_daily_main_archives.py").read_text(
            encoding="utf-8")
        self.assertIn('and report["uncertified_new_push_final_evidence_run_ids"]',
                      script)

    def test_uncertified_push_ignores_bad_run_metadata(self):
        row = {"run_id": 960, "created_at": "invalid",
               "artifact_present": True, "publication_outcome": "pushed_to_main",
               "final_evidence_verdict_status": "passed"}
        self.assertEqual(uncertified_new_push_final_evidence_run_ids(
            "20261104", [{"runs": [row]}]), [])

    def test_new_published_run_missing_final_verdict_is_explicit_unknown_alert(self):
        good = {"run_id": 901, "created_at": "2026-11-04T00:07:00Z",
                "artifact_present": True, "publication_outcome": "pushed_to_main",
                "final_evidence_verdict_status": "passed"}
        missing = {**good, "run_id": 902,
                   "final_evidence_verdict_status": None}
        noop = {**missing, "run_id": 903,
                "publication_outcome": "no_eligible_candidates"}
        old = {**missing, "run_id": 904,
               "created_at": "2026-11-03T00:07:00Z"}
        absent = {**missing, "run_id": 905, "artifact_present": False}
        report = {"runs": [good, missing, noop, old, absent]}
        self.assertEqual(missing_new_push_final_evidence_run_ids(
            "20261104", [report, {"runs": [dict(missing)]}]), [902])
        self.assertEqual(missing_new_push_final_evidence_run_ids(
            "20261103", [report]), [])
        self.assertEqual(missing_new_push_final_evidence_run_ids(
            "20261105", [report]), [])
        source = Path("scripts/audit_four_mode_daily_main_archives.py").read_text(
            encoding="utf-8")
        self.assertIn('and report["missing_new_push_final_evidence_run_ids"]', source)

    def test_legacy_or_invalid_run_does_not_become_fabricated_failure(self):
        row = {"run_id": 907, "created_at": "bad-date",
               "publication_outcome": "pushed_to_main",
               "final_evidence_verdict_status": None,
               "artifact_present": True}
        self.assertEqual(missing_new_push_final_evidence_run_ids(
            "20261104", [{"runs": [row]}]), [])

    def test_explicit_final_gate_failure_alerts_only_matching_jst_day(self):
        failed = {"run_id": 501, "created_at": "2026-11-03T15:05:00Z",
                  "final_evidence_verdict_status": "failed",
                  "final_evidence_verdict_error_type": "ValueError"}
        prior = {"run_id": 502, "created_at": "2026-11-03T14:59:00Z",
                 "final_evidence_verdict_status": "failed"}
        passed = {"run_id": 503, "created_at": "2026-11-03T15:09:00Z",
                  "final_evidence_verdict_status": "passed"}
        legacy = {"run_id": 504, "created_at": "2026-11-03T15:10:00Z"}
        evidence = [{"runs": [failed, prior, passed, legacy]},
                    {"runs": [{**failed}]}]
        self.assertEqual(final_evidence_failure_run_ids("20261104", evidence), [501])
        self.assertEqual(final_evidence_failure_run_ids("20261103", evidence), [502])

    def test_explicit_final_gate_failure_cannot_be_hidden_by_older_good_push(self):
        row = {"run_id": 510, "created_at": "2026-11-04T00:22:00Z",
               "publication_outcome": "pushed_to_main",
               "final_evidence_verdict_status": "failed"}
        self.assertEqual(final_evidence_failure_run_ids("20261104", [{"runs": [row]}]), [510])
        source = Path("scripts/audit_four_mode_daily_main_archives.py").read_text(
            encoding="utf-8")
        self.assertIn('and report["final_evidence_failure_run_ids"]', source)

    def test_server_observation_false_count_mismatch_triggers_daily_failure(self):
        evidence = {"runs": [{
            "run_id": 801, "created_at": "2026-11-04T00:07:00Z",
            "github_observation_integrity": {
                "status": "mismatch",
                "reason": "observation_count_disagrees_with_rows"}}]}
        self.assertEqual(github_observation_failure_run_ids(
            "20261104", [evidence]), [801])
        self.assertEqual(github_observation_failure_run_ids(
            "20261105", [evidence]), [])

    def test_server_observation_failure_checked_only_on_matching_day(self):
        current = {"run_id": 801, "created_at": "2026-11-04T00:07:00Z",
                   "github_observation_ledger_status": "observation_preservation_failed"}
        old = {"run_id": 800, "created_at": "2026-11-03T00:07:00Z",
               "github_server_observation_outcome": "failure"}
        self.assertEqual(github_observation_failure_run_ids(
            "20261104", [{"runs": [current, old]}]), [801])
        self.assertEqual(github_observation_failure_run_ids(
            "20261105", [{"runs": [current]}]), [])

    def test_scheduled_ledger_failure_is_day_scoped_and_not_hidden(self):
        day = {"run_id": 415, "created_at": "2026-11-04T00:07:00Z",
               "third_rate_ledger_outcome": "failure"}
        older = {"run_id": 414, "created_at": "2026-11-03T00:07:00Z",
                 "third_rate_ledger_status": "ledger_preservation_failed"}
        duplicated = {**day}
        self.assertEqual(ledger_failure_run_ids(
            "20261104", [{"runs": [day, older]},
                         {"runs": [duplicated]}]), [415])
        self.assertEqual(ledger_failure_run_ids("20261105", [{"runs": [day]}]), [])

    def test_research_roster_exactly_matches_git_first_add_ids(self):
        row = {"run_id": 415, "created_at": "2026-11-04T00:07:00Z",
               "publication_outcome": "pushed_to_main",
               "claimed_commit_sha": A, "claimed_added_forecasts": 2,
               "research_roster_evidence": {
                   "status": "matched", "commit_sha": A,
                   "race_codes": ["202611040102", "202611040101"]}}
        matched, bad, unknown = reconcile_research_rosters_with_main(
            "20261104", [P, P2], {P: [A], P2: [A]}, [{"runs": [row]}])
        self.assertEqual([x["run_id"] for x in matched], [415])
        self.assertEqual((bad, unknown), ([], []))

    def test_research_roster_wrong_ids_cannot_pass_equal_git_count(self):
        other = "four_mode_forecasts/202611040103.json"
        row = {"run_id": 415, "created_at": "2026-11-04T00:07:00Z",
               "publication_outcome": "pushed_to_main",
               "claimed_commit_sha": A, "claimed_added_forecasts": 2,
               "research_roster_evidence": {
                   "status": "matched", "commit_sha": A,
                   "race_codes": ["202611040101", "202611040103"]}}
        matched, bad, unknown = reconcile_research_rosters_with_main(
            "20261104", [P, P2], {P: [A], P2: [A]}, [{"runs": [row]}])
        self.assertEqual((matched, unknown), ([], []))
        self.assertEqual(bad[0]["research_only"], ["202611040103"])
        self.assertEqual(bad[0]["git_only"], ["202611040102"])

    def test_explicit_shadow_artifact_mismatch_is_not_silently_unknown(self):
        row = {"run_id": 415, "created_at": "2026-11-04T00:07:00Z",
               "publication_outcome": "pushed_to_main",
               "claimed_commit_sha": A, "claimed_added_forecasts": 2,
               "research_roster_evidence": {
                   "status": "mismatch", "reason": "shadow_race_rosters_disagree"}}
        matched, bad, unknown = reconcile_research_rosters_with_main(
            "20261104", [P, P2], {P: [A], P2: [A]}, [{"runs": [row]}])
        self.assertEqual((matched, unknown), ([], []))
        self.assertEqual(bad, [{
            "run_id": 415, "reason": "research_artifacts_disagree",
            "artifact_reason": "shadow_race_rosters_disagree"}])

    def test_old_or_missing_shadow_artifact_stays_unknown(self):
        row = {"run_id": 415, "created_at": "2026-11-04T00:07:00Z",
               "publication_outcome": "pushed_to_main",
               "claimed_commit_sha": A, "claimed_added_forecasts": 2,
               "research_roster_evidence": {
                   "status": "unknown", "reason": "research_artifact_missing"}}
        matched, bad, unknown = reconcile_research_rosters_with_main(
            "20261104", [P, P2], {P: [A], P2: [A]}, [{"runs": [row]}])
        self.assertEqual((matched, bad, unknown), ([], [], [415]))

    def test_legacy_missing_research_roster_is_unknown_not_error(self):
        row = {"run_id": 415, "created_at": "2026-11-04T00:07:00Z",
               "publication_outcome": "pushed_to_main",
               "claimed_commit_sha": A, "claimed_added_forecasts": 1}
        matched, bad, unknown = reconcile_research_rosters_with_main(
            "20261104", [P], {P: [A]}, [{"runs": [row]}])
        self.assertEqual((matched, bad, unknown), ([], [], [415]))

    def test_later_unpublished_candidates_detected_after_prior_good_push(self):
        evidence = {"runs": [
            {"run_id": 410, "created_at": "2026-11-04T00:07:00Z",
             "artifact_present": True, "newly_generated": 2,
             "staged_valid": 2, "publication_outcome": "pushed_to_main",
             "claimed_added_forecasts": 2},
            {"run_id": 411, "created_at": "2026-11-04T00:22:00Z",
             "artifact_present": True, "newly_generated": 1,
             "staged_valid": 1, "publication_outcome": "failed"},
            {"run_id": 412, "created_at": "2026-11-04T00:37:00Z",
             "artifact_present": True, "newly_generated": 0,
             "staged_valid": 0, "publication_outcome": "no_eligible_candidates"}]}
        broken = unpublished_new_candidate_runs("20261104", [evidence])
        self.assertEqual([r["run_id"] for r in broken], [411])
        self.assertEqual(broken[0]["reason"], "new_candidates_without_successful_push")
        # This is an independent alert even with existing 11/4 Git archives.
        report = audit("20261104", [P, P2], {P: [A], P2: [A]}, main_context=True)
        self.assertEqual(report["assessment"], "new_day_git_archives_found")
        script = Path("scripts/audit_four_mode_daily_main_archives.py").read_text(
            encoding="utf-8")
        self.assertIn('and report["unpublished_new_candidate_runs"]', script)

    def test_partially_pushed_same_run_is_an_explicit_mismatch(self):
        evidence = {"runs": [{
            "run_id": 420, "created_at": "2026-11-04T00:07:00Z",
            "artifact_present": True, "newly_generated": 3,
            "staged_valid": 3, "publication_outcome": "pushed_to_main",
            "claimed_added_forecasts": 2}]}
        problem = unpublished_new_candidate_runs("20261104", [evidence])
        self.assertEqual([x["run_id"] for x in problem], [420])
        self.assertEqual(problem[0]["reason"], "candidate_count_exceeds_push_claim")

    def test_new_candidate_failure_is_day_scoped_and_deduplicated(self):
        row = {"run_id": 430, "created_at": "2026-11-04T00:07:00Z",
               "artifact_present": True, "newly_generated": 1,
               "staged_valid": 0, "publication_outcome": "no_eligible_candidates"}
        # Generated-but-expired candidates are deliberately NOT staged.
        self.assertEqual(unpublished_new_candidate_runs(
            "20261104", [{"runs": [row]}, {"runs": [{**row}]}]), [])
        self.assertEqual([r["run_id"] for r in unpublished_new_candidate_runs(
            "20261104", [{"runs": [{**row, "staged_valid": 1}]},
                         {"runs": [{**row, "staged_valid": 1}]}])], [430])
        self.assertEqual(unpublished_new_candidate_runs(
            "20261105", [{"runs": [row]}]), [])
        self.assertEqual(unpublished_new_candidate_runs(
            "20261104", [{"runs": [{**row, "artifact_present": False}]}]), [])
        self.assertEqual(unpublished_new_candidate_runs(
            "20261104", [{"runs": [{**row, "newly_generated": None,
                                  "staged_valid": None}]}]), [])

    def test_expired_generated_candidates_are_not_false_publication_failures(self):
        base = {"run_id": 431, "created_at": "2026-11-04T00:07:00Z",
                "artifact_present": True, "newly_generated": 3,
                "staged_valid": 0, "publication_outcome": "no_eligible_candidates"}
        self.assertEqual(unpublished_new_candidate_runs(
            "20261104", [{"runs": [base]}]), [])
        # One safe race was staged and pushed; other generated candidates
        # expired before the staging gate and must not cause a false alarm.
        good = {**base, "staged_valid": 1,
                "publication_outcome": "pushed_to_main",
                "claimed_added_forecasts": 1}
        self.assertEqual(unpublished_new_candidate_runs(
            "20261104", [{"runs": [good]}]), [])
        # A staged valid race without any publication remains a real loss.
        bad = {**base, "staged_valid": 1}
        self.assertEqual([r["run_id"] for r in unpublished_new_candidate_runs(
            "20261104", [{"runs": [bad]}])], [431])
        # Failure before staging is still visible when new work existed.
        failed = {**base, "staged_valid": None, "publication_outcome": "failed"}
        self.assertEqual([r["run_id"] for r in unpublished_new_candidate_runs(
            "20261104", [{"runs": [failed]}])], [431])

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

    def test_evening_archive_audit_runs_after_last_planned_capture(self):
        workflow = Path(".github/workflows/four-mode-schedule-inventory.yml").read_text(
            encoding="utf-8")
        capture = Path(".github/workflows/four-mode-prospective-capture.yml").read_text(
            encoding="utf-8")
        # 09:20 and 22:20 JST must both remain configured.
        self.assertIn("- cron: '20 0 * * *'", workflow)
        self.assertIn("- cron: '20 13 * * *'", workflow)
        # Latest planned capture: 11:52 UTC = 20:52 JST.
        self.assertIn("- cron: '7,22,37,52 0-11 * * *'", capture)
        self.assertIn("git fetch --no-tags origin main", workflow)
        self.assertIn("reports/four_mode_daily_main_archives.json", workflow)
        self.assertIn("exhaustive per-run evidence for all 56 scheduled captures", workflow)

    def test_scheduled_git_audit_refreshes_main_after_artifact_downloads(self):
        workflow = Path(".github/workflows/four-mode-schedule-inventory.yml").read_text(
            encoding="utf-8")
        refresh = "name: Refresh remote main before final Git publication audit"
        audit = "name: Confirm today's first-add archive presence in checked-out Git main"
        self.assertIn(refresh, workflow)
        self.assertIn("if: always() && github.event_name == 'schedule' && github.ref == 'refs/heads/main'", workflow)
        self.assertIn("git fetch --no-tags origin main", workflow)
        self.assertIn("git checkout --detach FETCH_HEAD", workflow)
        self.assertLess(workflow.index("name: Audit watchdog decision artifacts"),
                        workflow.index(refresh))
        self.assertLess(workflow.index(refresh), workflow.index(audit))
        self.assertIn(audit + "\\n        if: always()".replace("\\n", "\n"), workflow)

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
