"""Fail-closed tests for the actual-saved-shadow vs separate four-mode audit."""
import copy
import hashlib
import unittest
from nov05_cross_artifact_reconcile import reconcile, TOPS, EXPECTED_N

CODES = [f"20261105{venue:02d}{race:02d}"
         for venue in range(1, 10) for race in range(1, 13)][:EXPECTED_N]


def fixtures():
    score = []
    historical = []
    for i, code in enumerate(CODES):
        old, new = i == 0, i == 1
        bits = {key: {"baseline": old, "candidate": new,
                      "gained": new and not old, "lost": old and not new}
                for key in TOPS}
        score.append({
            "race_code": code,
            "status": "matched_saved_shadow_and_remote_observation_research_only",
            "formal": False,
            "independent_first_receipt_verified": False,
            "complete_capture_run_inventory_verified": False,
            "official_six_boat_beforeinfo_verified": False,
            "winning_ticket": "1-2-3",
            "topn": bits,
        })
        reason = "covered" if old else "winner_second_pair_absent"
        historical.append({
            "race_code": code, "winning_ticket": "1-2-3",
            "modes": {mode: {
                **{key: old if mode == "hole" else False for key in TOPS},
                "coverage_diagnostic": reason
            } for mode in ("narrow", "hit", "balance", "hole")}
        })
    digest = hashlib.sha256(("\n".join(sorted(CODES)) + "\n").encode()).hexdigest()
    metrics = {key: {"baseline_hits": 1, "candidate_hits": 1,
                     "gained": 1, "lost": 1} for key in TOPS}
    saved = {
        "schema": "HOLE_NOV05_SAME_JOB_DIAGNOSTIC_V1",
        "status": "saved_candidate_result_comparison_research_only",
        "capture_run_id": 41953950959, "published_frozen": EXPECTED_N,
        "pre_result_consistent": EXPECTED_N,
        "confirmed_result_content_scored": EXPECTED_N,
        "pending_result_codes": [], "invalid_result_evidence": [],
        "formal": False, "model_improvement_proven": False,
        "pre_result_roster_committed_before_results": False,
        "pre_result_ticket_roster_sha256": "a" * 64,
        "per_race_result_diagnostic": score,
        "paired_historical_topn": metrics,
    }
    snapshot = {
        "schema": "FOUR_MODE_NOV05_MAIN_SNAPSHOT_HISTORICAL_AUDIT_V1",
        "status": "main_snapshot_research_comparable",
        "day_jst": "20261105", "examined_main_sha": "b" * 40,
        "four_mode_original_files": EXPECTED_N,
        "four_mode_result_filename_intersection": EXPECTED_N,
        "result_content_comparable_count": EXPECTED_N,
        "untrusted_or_invalid_result_rows": [],
        "forecasts_without_result_filename": [],
        "formal": False, "prospective_accuracy_verified": False,
        "intersection_race_codes": sorted(CODES),
        "intersection_sha256": digest,
        "historical_per_race": historical,
        "historical_topn_hits": {"hole": {key: 1 for key in TOPS}},
        "historical_coverage_miss_reasons": {
            "hole": {"covered": 1, "winner_second_pair_absent": 105}},
    }
    return saved, snapshot


class CrossAuditTests(unittest.TestCase):
    def test_exact_106_consistency_no_formal_promotion(self):
        saved, snapshot = fixtures()
        r = reconcile(saved, snapshot)
        self.assertEqual(r["status"], "cross_source_consistent_research_only")
        self.assertEqual(r["common_result_validated_races"], 106)
        self.assertEqual(r["topn"]["top10"]["gained"], 1)
        self.assertEqual(r["topn"]["top10"]["lost"], 1)
        self.assertEqual(r["topn"]["top10"]["net"], 0)
        self.assertEqual(len(r["per_race"]), 106)
        self.assertFalse(r["formal"])
        self.assertFalse(r["complete_forward_300_enrollment_verified"])

    def test_result_ticket_mismatch_fails_closed(self):
        a, b = fixtures()
        b["historical_per_race"][1]["winning_ticket"] = "1-3-2"
        with self.assertRaisesRegex(ValueError, "race_provenance_or_result_mismatch"):
            reconcile(a, b)

    def test_saved_candidate_flag_mismatch_fails_closed(self):
        a, b = fixtures()
        a["per_race_result_diagnostic"][1]["topn"]["top10"]["candidate"] = False
        with self.assertRaisesRegex(ValueError, "saved_shadow_vs_four_mode_disagrees"):
            reconcile(a, b)

    def test_swapped_race_id_fails_closed(self):
        a, b = fixtures()
        b["historical_per_race"][1]["race_code"] = "202611051012"
        with self.assertRaisesRegex(ValueError, "different_saved_and_snapshot_races"):
            reconcile(a, b)

    def test_duplicate_race_id_fails_closed(self):
        a, b = fixtures()
        b["historical_per_race"][1]["race_code"] = CODES[0]
        with self.assertRaisesRegex(ValueError, "invalid_or_duplicate_cross_race"):
            reconcile(a, b)

    def test_missing_result_for_one_race_withholds_comparison(self):
        a, b = fixtures()
        a["confirmed_result_content_scored"] = 105
        with self.assertRaisesRegex(ValueError, "cross_report_not_fully_research_comparable"):
            reconcile(a, b)

    def test_forged_formal_label_rejected(self):
        a, b = fixtures()
        a["formal"] = True
        with self.assertRaisesRegex(ValueError, "cross_report_not_fully_research_comparable"):
            reconcile(a, b)

    def test_false_pre_result_cohort_claim_rejected(self):
        a, b = fixtures()
        a["pre_result_roster_committed_before_results"] = True
        with self.assertRaisesRegex(ValueError, "cross_report_not_fully_research_comparable"):
            reconcile(a, b)


if __name__ == "__main__":
    unittest.main()
