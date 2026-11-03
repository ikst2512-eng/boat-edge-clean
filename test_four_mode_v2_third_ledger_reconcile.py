import unittest

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
            "race_codes_frozen": [A, B],
            "missing_or_failed_artifacts": [],
            "bad_validation_runs": [],
        }
        self.ledger = {
            "schema": "V2_THIRD_RATE_DURABLE_LEDGER_SCORE_V1",
            "status": "durable_frozen_evidence_scored",
            "frozen": 3,
            "race_codes_frozen": [A, B, C],
            "invalid_files": [],
        }

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

    def test_no_candidate_is_not_hit_or_long_term_success(self):
        self.capture.update({"frozen": 0, "race_codes_frozen": []})
        report = reconcile(self.capture, self.ledger)
        self.assertEqual(report["status"], "no_frozen_predictions_to_compare")
        self.assertEqual(report["missing_from_ledger"], [])

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
