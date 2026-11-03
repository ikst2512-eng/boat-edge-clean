import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from four_mode_v2_third_ledger_reconcile import reconcile

A = "202611040101"
B = "202611040102"
C = "202611050101"


class FrozenLedgerReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.capture = {
            "schema": "V2_THIRD_RATE_FROZEN_NIGHTLY_ARTIFACT_AUDIT_V1",
            "status": "frozen_artifacts_scored_limited_cohort",
            "cohort_completeness_verified": True,
            "frozen": 2,
            "paired": 0, "paired_race_scores": [], "race_codes_paired": [],
            "race_codes_frozen": [A, B],
            "missing_or_failed_artifacts": [],
            "bad_validation_runs": [],
        }
        self.ledger = {
            "schema": "V2_THIRD_RATE_DURABLE_LEDGER_SCORE_V1",
            "status": "durable_frozen_evidence_scored",
            "frozen": 3,
            "paired": 0, "paired_race_scores": [], "race_codes_paired": [],
            "race_codes_frozen": [A, B, C],
            "invalid_files": [],
        }


    @staticmethod
    def race_score(code, baseline=0, candidate=0):
        gain = int(candidate > baseline)
        lost = int(baseline > candidate)
        return {"race_code": code, "topn": {
            name: {"baseline": baseline, "candidate": candidate,
                   "gained": gain, "lost": lost}
            for name in ("top3", "top5", "top10")}}

    def test_same_race_equal_frozen_roster_but_different_hits_fails(self):
        self.capture.update({"paired": 1, "race_codes_paired": [A],
                             "paired_race_scores": [self.race_score(A, 0, 1)]})
        self.ledger.update({"paired": 1, "race_codes_paired": [A],
                            "paired_race_scores": [self.race_score(A, 1, 0)]})
        report = reconcile(self.capture, self.ledger)
        self.assertEqual(report["status"], "paired_topn_score_mismatch")
        self.assertEqual(report["paired_score_mismatch_codes"], [A])

    def test_matching_per_race_hits_allow_older_ledger_races(self):
        row = self.race_score(A, 0, 1)
        self.capture.update({"paired": 1, "race_codes_paired": [A],
                             "paired_race_scores": [row]})
        self.ledger.update({"paired": 2, "race_codes_paired": [A, C],
                            "paired_race_scores": [row, self.race_score(C, 1, 1)]})
        report = reconcile(self.capture, self.ledger)
        self.assertEqual(report["status"], "bounded_frozen_roster_matched")
        self.assertEqual(report["paired_score_mismatch_codes"], [])

    def test_ledger_result_absent_from_capture_is_not_match(self):
        # The exact inverse of the older capture-only coverage check:
        # both producers have the same frozen race, but only ledger scored it.
        self.ledger.update({
            "paired": 1, "race_codes_paired": [A],
            "paired_race_scores": [self.race_score(A, 1, 1)]})
        report = reconcile(self.capture, self.ledger)
        self.assertEqual(report["status"], "paired_result_coverage_mismatch")
        self.assertEqual(report["paired_result_coverage_mismatch_codes"], [A])

    def test_older_ledger_result_outside_capture_freeze_is_ignored(self):
        self.ledger.update({
            "paired": 1, "race_codes_paired": [C],
            "paired_race_scores": [self.race_score(C, 1, 1)]})
        report = reconcile(self.capture, self.ledger)
        self.assertEqual(report["status"], "bounded_frozen_roster_matched")
        self.assertEqual(report["paired_result_coverage_mismatch_codes"], [])

    def test_capture_paired_result_absent_from_ledger_is_not_match(self):
        self.capture.update({"paired": 1, "race_codes_paired": [A],
                             "paired_race_scores": [self.race_score(A, 1, 1)]})
        report = reconcile(self.capture, self.ledger)
        self.assertEqual(report["status"], "paired_result_coverage_mismatch")
        self.assertEqual(report["paired_result_coverage_mismatch_codes"], [A])

    def test_missing_per_race_score_refuses_matched_status(self):
        self.capture.update({"paired": 1, "race_codes_paired": [A]})
        self.assertEqual(reconcile(self.capture, self.ledger)["status"],
                         "paired_score_evidence_missing_or_invalid")

    def test_matching_bounded_capture_subset_does_not_require_older_ledger_entries(self):
        report = reconcile(self.capture, self.ledger)
        self.assertEqual(report["status"], "bounded_frozen_roster_matched")
        self.assertEqual(report["missing_from_ledger"], [])
        self.assertEqual(report["additional_ledger_codes"], [C])
        self.assertFalse(report["formal"])
        self.assertFalse(report["remote_first_seen_independently_verified"])

    def test_equal_counts_but_wrong_race_ids_are_not_matched(self):
        self.ledger["race_codes_frozen"] = [A, C]
        self.ledger["frozen"] = 2
        report = reconcile(self.capture, self.ledger)
        self.assertEqual(report["status"], "frozen_predictions_missing_from_ledger")
        self.assertEqual(report["missing_from_ledger"], [B])

    def test_both_empty_complete_capture_and_empty_ledger_are_not_corruption(self):
        self.capture.update({"frozen": 0, "race_codes_frozen": []})
        self.ledger.update({"status": "no_long_lived_frozen_evidence",
                            "frozen": 0, "race_codes_frozen": []})
        result = reconcile(self.capture, self.ledger)
        self.assertEqual(result["status"], "no_frozen_predictions_to_compare")
        self.assertEqual(result["missing_from_ledger"], [])
        self.assertFalse(result["formal"])
        self.assertFalse(result["production_promotion_allowed"])

    def test_empty_ledger_status_cannot_hide_missing_frozen_races(self):
        self.ledger.update({"status": "no_long_lived_frozen_evidence",
                            "frozen": 0, "race_codes_frozen": []})
        report = reconcile(self.capture, self.ledger)
        self.assertEqual(report["status"], "invalid_or_unavailable_ledger")
        self.assertEqual(report["missing_from_ledger"], [A, B])

    def test_empty_ledger_status_with_positive_ledger_count_is_invalid(self):
        self.capture.update({"frozen": 0, "race_codes_frozen": []})
        self.ledger["status"] = "no_long_lived_frozen_evidence"
        self.assertEqual(reconcile(self.capture, self.ledger)["status"],
                         "invalid_or_unavailable_ledger")

    def test_no_candidate_is_not_hit_or_long_term_success(self):
        self.capture.update({"frozen": 0, "race_codes_frozen": []})
        report = reconcile(self.capture, self.ledger)
        self.assertEqual(report["status"], "no_frozen_predictions_to_compare")
        self.assertEqual(report["missing_from_ledger"], [])

    def test_prestart_future_zero_cohort_is_neutral_not_accuracy(self):
        self.capture.update({
            "status": "no_future_capture_runs",
            "cohort_completeness_verified": False,
            "frozen": 0, "paired": 0,
            "race_codes_frozen": [], "race_codes_paired": [],
            "eligible_runs_in_inventory": 0, "selected_runs": 0,
            "pending_or_unknown_runs": 0, "unsuccessful_runs": 0,
            "inventory_limit_reached": False,
        })
        self.ledger.update({
            "status": "no_long_lived_frozen_evidence",
            "frozen": 0, "paired": 0,
            "race_codes_frozen": [], "race_codes_paired": [],
        })
        report = reconcile(self.capture, self.ledger, before_future_start=True)
        self.assertEqual(report["status"], "prestart_no_future_capture_runs")
        self.assertFalse(report["production_promotion_allowed"])
        self.assertFalse(report["formal"])
        self.assertFalse(report["remote_first_seen_independently_verified"])
        self.assertEqual(reconcile(self.capture, self.ledger,
                                   before_future_start=False)["status"],
                         "incomplete_capture_inventory")

    def test_prestart_neutral_exemption_never_hides_missing_or_failed_evidence(self):
        self.capture.update({
            "status": "no_future_capture_runs",
            "cohort_completeness_verified": False,
            "frozen": 0, "paired": 0,
            "race_codes_frozen": [], "race_codes_paired": [],
            "eligible_runs_in_inventory": 0, "selected_runs": 0,
            "pending_or_unknown_runs": 0, "unsuccessful_runs": 0,
            "inventory_limit_reached": False,
        })
        self.ledger.update({
            "status": "no_long_lived_frozen_evidence",
            "frozen": 0, "paired": 0,
            "race_codes_frozen": [], "race_codes_paired": [],
        })
        for field, invalid in (
            ("inventory_limit_reached", True),
            ("eligible_runs_in_inventory", 1),
            ("selected_runs", 1),
            ("pending_or_unknown_runs", 1),
            ("unsuccessful_runs", 1),
            ("missing_or_failed_artifacts", [12]),
            ("bad_validation_runs", [12]),
            ("frozen", 1),
        ):
            with self.subTest(field=field):
                previous = self.capture.get(field)
                self.capture[field] = invalid
                result = reconcile(self.capture, self.ledger,
                                   before_future_start=True)
                self.assertNotEqual(result["status"], "prestart_no_future_capture_runs")
                if field != "frozen":
                    self.assertEqual(result["status"], "incomplete_capture_inventory")
                if previous is None:
                    self.capture.pop(field, None)
                else:
                    self.capture[field] = previous

    def test_prestart_requires_truly_empty_long_term_ledger(self):
        self.capture.update({
            "status": "no_future_capture_runs",
            "frozen": 0, "paired": 0,
            "race_codes_frozen": [],
            "eligible_runs_in_inventory": 0, "selected_runs": 0,
            "pending_or_unknown_runs": 0, "unsuccessful_runs": 0,
            "inventory_limit_reached": False,
        })
        self.ledger.update({
            "status": "durable_frozen_evidence_scored",
            "frozen": 0, "race_codes_frozen": [],
        })
        self.assertNotEqual(
            reconcile(self.capture, self.ledger,
                      before_future_start=True)["status"],
            "prestart_no_future_capture_runs")

    def test_cli_incomplete_capture_fails_ci_but_preserves_diagnostic_json(self):
        self.capture["status"] = "incomplete_capture_run_outcomes"
        self.capture["cohort_completeness_verified"] = False
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            capture = root / "capture.json"
            ledger = root / "ledger.json"
            report = root / "reconciliation.json"
            capture.write_text(json.dumps(self.capture), encoding="utf-8")
            ledger.write_text(json.dumps(self.ledger), encoding="utf-8")
            proc = subprocess.run([
                sys.executable,
                str(Path(__file__).with_name("four_mode_v2_third_ledger_reconcile.py")),
                "--capture", str(capture), "--ledger", str(ledger),
                "--output", str(report),
            ], capture_output=True, text=True, timeout=20)
            self.assertEqual(proc.returncode, 2, proc.stderr)
            self.assertEqual(json.loads(report.read_text(encoding="utf-8"))["status"],
                             "incomplete_capture_inventory")

    def test_cli_missing_ledger_writes_diagnostic_and_exits_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            capture = root / "capture.json"
            ledger = root / "missing_ledger.json"
            report = root / "reconciliation.json"
            capture.write_text(json.dumps(self.capture), encoding="utf-8")
            proc = subprocess.run([
                sys.executable,
                str(Path(__file__).with_name("four_mode_v2_third_ledger_reconcile.py")),
                "--capture", str(capture), "--ledger", str(ledger),
                "--output", str(report),
            ], capture_output=True, text=True, timeout=20)
            self.assertEqual(proc.returncode, 2, proc.stderr)
            data = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(data["status"], "reconciliation_inputs_unavailable")
            self.assertEqual(data["missing_input_reports"], ["ledger"])
            self.assertFalse(data["production_promotion_allowed"])

    def test_cli_invalid_capture_json_preserves_diagnostic(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            capture = root / "capture.json"
            ledger = root / "ledger.json"
            report = root / "reconciliation.json"
            capture.write_text("{not-json", encoding="utf-8")
            ledger.write_text(json.dumps(self.ledger), encoding="utf-8")
            proc = subprocess.run([
                sys.executable,
                str(Path(__file__).with_name("four_mode_v2_third_ledger_reconcile.py")),
                "--capture", str(capture), "--ledger", str(ledger),
                "--output", str(report),
            ], capture_output=True, text=True, timeout=20)
            self.assertEqual(proc.returncode, 2, proc.stderr)
            data = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(data["status"], "reconciliation_inputs_unavailable")
            self.assertEqual(data["invalid_input_reports"], ["capture"])

    def test_cli_wrong_report_schema_preserves_diagnostic(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            capture = root / "capture.json"
            ledger = root / "ledger.json"
            report = root / "reconciliation.json"
            capture.write_text(json.dumps({"schema":"INVALID"}), encoding="utf-8")
            ledger.write_text(json.dumps(self.ledger), encoding="utf-8")
            proc = subprocess.run([
                sys.executable,
                str(Path(__file__).with_name("four_mode_v2_third_ledger_reconcile.py")),
                "--capture", str(capture), "--ledger", str(ledger),
                "--output", str(report),
            ], capture_output=True, text=True, timeout=20)
            self.assertEqual(proc.returncode, 2, proc.stderr)
            data = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(data["status"], "reconciliation_input_schema_invalid")

    def test_cli_bounded_matched_roster_succeeds(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            capture = root / "capture.json"
            ledger = root / "ledger.json"
            report = root / "reconciliation.json"
            capture.write_text(json.dumps(self.capture), encoding="utf-8")
            ledger.write_text(json.dumps(self.ledger), encoding="utf-8")
            proc = subprocess.run([
                sys.executable,
                str(Path(__file__).with_name("four_mode_v2_third_ledger_reconcile.py")),
                "--capture", str(capture), "--ledger", str(ledger),
                "--output", str(report),
            ], capture_output=True, text=True, timeout=20)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(json.loads(report.read_text(encoding="utf-8"))["status"],
                             "bounded_frozen_roster_matched")

    def test_truncated_capture_is_incomplete_even_when_subset_matches(self):
        self.capture["status"] = "incomplete_run_inventory_coverage"
        self.capture["cohort_completeness_verified"] = False
        report = reconcile(self.capture, self.ledger)
        self.assertEqual(report["status"], "incomplete_capture_inventory")

    def test_missing_artifact_prevents_success_verdict(self):
        self.capture["missing_or_failed_artifacts"] = [123]
        report = reconcile(self.capture, self.ledger)
        self.assertEqual(report["status"], "incomplete_capture_inventory")

    def test_unknown_capture_status_cannot_claim_matched_roster(self):
        for state in ("unexpected_success", "scored_frozen_artifacts",
                      "no_future_capture_runs", None):
            with self.subTest(state=state):
                self.capture["status"] = state
                self.assertEqual(reconcile(self.capture, self.ledger)["status"],
                                 "incomplete_capture_inventory")

    def test_unexpected_ledger_status_cannot_claim_matched_roster(self):
        for state in ("unexpected_success", "no_long_lived_frozen_evidence", None):
            with self.subTest(state=state):
                self.ledger["status"] = state
                self.assertEqual(reconcile(self.capture, self.ledger)["status"],
                                 "invalid_or_unavailable_ledger")

    def test_missing_explicit_cohort_completeness_cannot_claim_match(self):
        self.capture["cohort_completeness_verified"] = 1
        self.assertEqual(reconcile(self.capture, self.ledger)["status"],
                         "incomplete_capture_inventory")

    def test_ledger_invalid_blocks_matched_claim(self):
        self.ledger["invalid_files"] = ["third_rate/bad.json"]
        report = reconcile(self.capture, self.ledger)
        self.assertEqual(report["status"], "invalid_or_unavailable_ledger")

    def test_duplicate_in_capture_or_ledger_rejected(self):
        self.capture["race_codes_frozen"] = [A, A]
        with self.assertRaisesRegex(ValueError, "invalid_frozen_race_rosters"):
            reconcile(self.capture, self.ledger)
        self.capture["race_codes_frozen"] = [A, B]
        self.ledger["race_codes_frozen"] = [A, A, C]
        with self.assertRaisesRegex(ValueError, "invalid_frozen_race_rosters"):
            reconcile(self.capture, self.ledger)

    def test_wrong_schema_fails_closed(self):
        self.capture["schema"] = "NOT_AN_AUDIT"
        with self.assertRaisesRegex(ValueError, "invalid_audit_schema"):
            reconcile(self.capture, self.ledger)


if __name__ == "__main__":
    unittest.main()
