"""Synthetic adversarial coverage; never contacts GitHub or opens race results."""
import copy
import hashlib
import unittest

from hole_pair_remote_receipt_evidence import canonical_bytes
from research.hole_pair_universe_coverage import reconcile
from research import hole_pair_cross_batch_roster as b
from test_hole_pair_remote_receipt_evidence import candidate

DAY = "20261109"
MAIN = "a" * 40
R1, R2, R3 = "202611090101", "202611090102", "202611090103"


def frozen(code=R1):
    record = candidate()
    record["race_code"] = code
    record["source_git_blob_sha1"] = "b" * 40
    record["model_version"] = "CLEAN_FOUR_MODES_V2_PROVISIONAL_UNCALIBRATED"
    record["locked_selector_git_blobs"] = {
        "hole_third_choice_research.py": "579edc1ae846489d447307fbf03b35fc7d4c09b9",
        "hole_pair_diversification_research.py": "56f06c10f6d07e03b2e37624ecf57dc6de7d8748",
        "hole_top5_safe_bundle_research.py": "a43f53d898ac73829e7f2b24f81624d69d26d74a",
        "hole_pair_third_bundle_research.py": "88c4ed506588a24bb593d104b5d0f59c7502d73a",
    }
    return record


def manifest(source_codes, records, excluded=None, main=MAIN):
    excluded = excluded or {}
    coverage = reconcile(DAY, main, source_codes, records, excluded)
    return {
        "schema": "HOLE_PAIR_FUTURE_ACTIONS_BATCH_V1",
        "status": "local_predeadline_freeze_not_formal",
        "capture_day_jst": DAY,
        "source_main_commit": main,
        "source_forecast_codes": source_codes,
        "source_snapshot_coverage": coverage,
        "records": records,
        "excluded_race_codes_by_reason": excluded,
        "eligible_forecasts_examined": len(source_codes),
        "frozen_count": len(records),
        "excluded_by_reason": coverage["excluded_by_reason"],
        "formal": False,
        "prospective_validation": False,
        "independent_first_receipt_verified": False,
        "production_forecast_changed": False,
    }


def observed(run, artifact, data, stamp="2026-11-09T01:55:00.000Z"):
    return {
        "run_id": run,
        "artifact_id": artifact,
        "artifact_observed_at_utc": stamp,
        "manifest_sha256": hashlib.sha256(canonical_bytes(data)).hexdigest(),
        "manifest": data,
    }


class CrossBatchRosterTests(unittest.TestCase):
    def test_same_candidate_across_runs_counts_once(self):
        data = manifest([R1], [frozen()])
        r = b.audit([
            observed(100, 200, data),
            observed(101, 201, copy.deepcopy(data), "2026-11-09T01:57:00.000Z"),
            observed(102, 202, copy.deepcopy(data), "2026-11-09T01:59:00.000Z"),
        ])
        self.assertEqual(r["artifacts_observed"], 3)
        self.assertEqual(r["race_observations_total"], 3)
        self.assertEqual(r["distinct_race_codes"], 1)
        self.assertEqual(r["unique_frozen_unverified"], 1)
        self.assertEqual(r["identical_frozen_repeats_not_added_to_denominator"], 2)
        self.assertEqual(r["quarantined_conflicts"], 0)
        self.assertEqual(r["formally_eligible"], 0)
        self.assertFalse(r["formal"])

    def test_different_candidate_bytes_cannot_replace_first_frozen(self):
        original = manifest([R1], [frozen()])
        other = frozen()
        other["local_finish_jst"] = "2026-11-09T10:52:00+09:00"
        altered = manifest([R1], [other])
        r = b.audit([observed(100, 200, original),
                     observed(101, 201, altered, "2026-11-09T01:58:00.000Z")])
        self.assertEqual(r["quarantined_conflicts"], 1)
        self.assertEqual(r["unique_frozen_unverified"], 0)
        self.assertTrue(r["rows"][0]["conflicting_frozen_record"])
        self.assertFalse(r["production_promotion_allowed"])

    def test_same_ticket_choices_but_changed_frozen_clock_is_conflict(self):
        a = manifest([R1], [frozen()])
        r2 = frozen()
        r2["local_start_jst"] = "2026-11-09T10:50:01+09:00"
        b2 = manifest([R1], [r2])
        report = b.audit([observed(100, 200, a), observed(101, 201, b2,
                        "2026-11-09T01:56:00.000Z")])
        self.assertEqual(report["quarantined_conflicts"], 1)

    def test_first_excluded_cannot_be_replaced_by_later_candidate(self):
        first = manifest([R1], [], {"after_t_minus_12": [R1]})
        second = manifest([R1], [frozen()])
        r = b.audit([observed(100, 200, first),
                     observed(101, 201, second, "2026-11-09T01:57:00.000Z")])
        self.assertEqual(r["quarantined_conflicts"], 1)
        self.assertTrue(r["rows"][0]["first_excluded_then_later_frozen"])
        self.assertEqual(r["formally_eligible"], 0)

    def test_equal_reported_time_with_incompatible_dispositions_is_quarantined(self):
        a = manifest([R1], [frozen()])
        b2 = manifest([R1], [], {"after_t_minus_12": [R1]})
        # Both apparent first clocks are equal: run ID cannot settle who came first.
        report = b.audit([
            observed(100, 200, a, "2026-11-09T01:55:00.000Z"),
            observed(101, 201, b2, "2026-11-09T01:55:00.000Z"),
        ])
        self.assertEqual(report["quarantined_conflicts"], 1)
        self.assertEqual(report["unique_frozen_unverified"], 0)
        self.assertTrue(report["rows"][0]["ambiguous_equal_time_first_disposition"])
        # Reverse run IDs: same quarantine, never let tiebreak order promote it.
        report2 = b.audit([
            observed(102, 202, a, "2026-11-09T01:55:00.000Z"),
            observed(99, 199, b2, "2026-11-09T01:55:00.000Z"),
        ])
        self.assertEqual(report2["quarantined_conflicts"], 1)
        self.assertTrue(report2["rows"][0]["ambiguous_equal_time_first_disposition"])

    def test_artifact_observation_before_local_candidate_finish_refused(self):
        data = manifest([R1], [frozen()])
        with self.assertRaisesRegex(
                ValueError, "artifact_observation_precedes_candidate_calculation"):
            b.audit([observed(100, 200, data, "2026-11-09T01:50:59.000Z")])

    def test_equal_time_different_exclusion_reasons_quarantined(self):
        x = manifest([R1], [], {"after_t_minus_12": [R1]})
        y = manifest([R1], [], {"invalid_deadline": [R1]})
        report = b.audit([
            observed(100, 200, x),
            observed(101, 201, y),
        ])
        self.assertEqual(report["quarantined_conflicts"], 1)
        self.assertEqual(report["initially_excluded"], 0)
        self.assertTrue(report["rows"][0]["ambiguous_equal_time_first_disposition"])

    def test_later_excluded_recheck_does_not_override_earliest_frozen(self):
        first = manifest([R1], [frozen()])
        second = manifest([R1], [], {"after_t_minus_12": [R1]})
        r = b.audit([observed(100, 200, first), observed(101, 201, second,
                     "2026-11-09T02:01:00.000Z")])
        self.assertEqual(r["unique_frozen_unverified"], 1)
        self.assertEqual(r["late_exclusions_after_first_frozen_reference"], 1)
        self.assertEqual(r["quarantined_conflicts"], 0)

    def test_repeated_exclusions_never_create_candidate(self):
        excluded = manifest([R1], [], {"after_t_minus_12": [R1]})
        r = b.audit([observed(100, 200, excluded), observed(101, 201, excluded,
                     "2026-11-09T02:01:00.000Z")])
        self.assertEqual(r["initially_excluded"], 1)
        self.assertEqual(r["unique_frozen_unverified"], 0)
        self.assertEqual(r["formally_eligible"], 0)

    def test_distinct_main_snapshots_overlap_without_double_count(self):
        a = manifest([R1, R2], [frozen(R1)], {"invalid_deadline": [R2]})
        q = manifest([R1, R3], [frozen(R1), frozen(R3)], main="c"*40)
        r = b.audit([observed(100, 200, a), observed(101, 201, q,
                     "2026-11-09T01:58:00.000Z")])
        self.assertEqual(r["distinct_race_codes"], 3)
        self.assertEqual(r["unique_frozen_unverified"], 2)
        self.assertEqual(r["initially_excluded"], 1)
        self.assertEqual(r["identical_frozen_repeats_not_added_to_denominator"], 1)

    def test_duplicate_run_artifact_identity_is_blocked(self):
        a = observed(100, 200, manifest([R1], [frozen()]))
        with self.assertRaisesRegex(ValueError, "duplicated_run_artifact_observation"):
            b.audit([a, a])

    def test_manifest_hash_mutation_fails_before_any_aggregation(self):
        a = observed(100, 200, manifest([R1], [frozen()]))
        a["manifest"]["frozen_count"] = 0
        with self.assertRaisesRegex(ValueError, "untrusted_artifact_manifest_digest"):
            b.audit([a])

    def test_edited_manifest_with_new_hash_still_fails_census(self):
        m = manifest([R1], [frozen()])
        m["source_forecast_codes"] = [R1, R2]
        obs = observed(100, 200, m)
        with self.assertRaisesRegex(ValueError, "coverage_mismatch|batch_and_source_snapshot"):
            b.audit([obs])

    def test_false_formal_claim_refused(self):
        m = manifest([R1], [frozen()])
        m["formal"] = True
        with self.assertRaisesRegex(ValueError, "untrusted_batch_status_or_formal_claim"):
            b.audit([observed(100, 200, m)])

    def test_duplicate_or_missing_source_id_in_batch_refused(self):
        m = manifest([R1], [frozen()])
        m["source_forecast_codes"] = [R1, R1]
        with self.assertRaisesRegex(ValueError, "duplicate_source_inventory"):
            b.audit([observed(100, 200, m)])

    def test_invalid_run_artifact_and_timestamp_refused(self):
        data = manifest([R1], [frozen()])
        for run, artifact, stamp in (
            (0, 200, "2026-11-09T01:55:00.000Z"),
            (100, -1, "2026-11-09T01:55:00.000Z"),
            (100, 200, "2026-11-09T10:55:00+09:00"),
            (100, 200, "not-a-timestamp"),
        ):
            with self.subTest(run=run, artifact=artifact, stamp=stamp):
                with self.assertRaises(ValueError):
                    b.audit([observed(run, artifact, data, stamp)])

    def test_out_of_protocol_day_cannot_backfill(self):
        m = manifest([R1], [frozen()])
        m["capture_day_jst"] = "20261108"
        with self.assertRaisesRegex(ValueError, "capture_day_outside_future_protocol"):
            b.audit([observed(100, 200, m)])

    def test_empty_run_cannot_be_mistaken_for_whole_day(self):
        r = b.audit([observed(100, 200, manifest([], []))])
        self.assertEqual(r["distinct_race_codes"], 0)
        self.assertFalse(r["official_day_schedule_coverage_verified"])
        self.assertEqual(r["pilot_formally_eligible"], 0)
        self.assertEqual(r["confirmation_formally_eligible"], 0)
        self.assertFalse(r["formal"])

    def test_no_external_receipt_or_official_t12_proof_from_artifact_metadata(self):
        m = manifest([R1], [frozen()])
        r = b.audit([observed(100, 200, m)])
        self.assertFalse(r["artifact_observation_time_independently_attested"])
        self.assertFalse(r["independent_first_receipt_verified"])
        self.assertFalse(r["official_t12_complete_verified"])
        self.assertEqual(r["formally_eligible"], 0)


if __name__ == "__main__":
    unittest.main()
