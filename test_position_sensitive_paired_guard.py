"""Safety tests for read-only #1698 aggregate TopK regression guard."""
from copy import deepcopy
import json
import unittest

from four_mode_position_sensitive_forward import compare_reference, MODES, TOPS
from position_sensitive_paired_guard import (
    GUARD_SCHEMA, assess_reference_score,
)
from test_four_mode_position_sensitive_forward import archive, frozen, result


def synthetic_reference(full=True):
    """Synthetic counters only; never offered as a real prospective result."""
    slots = 600 if full else 0
    count = 300 if full else 0
    result_counts = {"pilot": count, "confirmation": count} if full else {}
    phase_map = {}
    for phase in ("pilot", "confirmation"):
        phase_map[phase] = {}
        for mode in MODES:
            phase_map[phase][mode] = {}
            for top in TOPS:
                phase_map[phase][mode][str(top)] = {
                    "baseline": 0, "candidate": 0, "gained": 0, "lost": 0,
                    "reference_denominator": count,
                }
    return {
        "schema": "FOUR_MODE_POSITION_SENSITIVE_REFERENCE_SCORE_V1",
        "status": "reference_only_unverified_first_remote_receipt",
        "formal": False, "promotion_allowed": False,
        "model_improvement_proven": False,
        "candidate_first_remote_receipt_verified": False,
        "complete_capture_inventory_verified": False,
        "official_T12_beforeinfo_six_and_odds_120_verified": False,
        "eligible_frozen_candidate_slots": slots,
        "pilot_reserved_slots": 300 if full else 0,
        "confirmation_reserved_slots": 300 if full else 0,
        "confirmed_result_counts": result_counts,
        "pending_race_codes": [],
        "invalid_result_race_codes": [],
        "by_phase_mode_topn": phase_map,
    }


def set_paired(s, phase, mode, top, baseline, candidate, gained, lost):
    row = s["by_phase_mode_topn"][phase][mode][str(top)]
    row.update(baseline=baseline, candidate=candidate, gained=gained, lost=lost)


class PairedGuardTests(unittest.TestCase):
    def test_zero_samples_never_qualified(self):
        score = compare_reference([], {}, {})
        guarded = assess_reference_score(score)
        self.assertEqual(guarded["schema"], GUARD_SCHEMA)
        self.assertFalse(guarded["all_600_reference_results_present"])
        self.assertIsNone(guarded["reference_confirmatory_top5_top10_net_loss_observed"])
        self.assertIsNone(guarded["by_phase_mode_topn"]["pilot"]["hit"]["5"][
            "observed_net_regression"])
        self.assertFalse(guarded["promotion_allowed"])
        self.assertFalse(guarded["model_improvement_proven"])

    def test_real_reference_scorer_one_future_fixture_not_formal(self):
        snap, original = frozen()
        score = compare_reference(
            [snap], {snap["race_code"]: original},
            {snap["race_code"]: result(finish=(1, 2, 3))})
        guarded = assess_reference_score(score)
        hit_top1 = guarded["by_phase_mode_topn"]["pilot"]["hit"]["1"]
        self.assertEqual(hit_top1["gained_hits"], 1)
        self.assertEqual(hit_top1["lost_hits"], 0)
        self.assertEqual(hit_top1["reference_denominator"], 1)
        self.assertFalse(guarded["all_600_reference_results_present"])
        self.assertFalse(guarded["promotion_allowed"])
        narrow = guarded["by_phase_mode_topn"]["pilot"]["narrow"]["10"]
        self.assertFalse(narrow["applicable"])
        self.assertEqual(narrow["mode_ticket_budget"], 5)

    def test_explicit_counterexample_top1_improves_but_top5_top10_regress(self):
        score = synthetic_reference(full=True)
        for phase in ("pilot", "confirmation"):
            for top, vals in {
                "1": (80, 90, 20, 10),
                "3": (120, 124, 14, 10),
                "5": (140, 135, 15, 20),
                "10": (170, 165, 20, 25),
            }.items():
                set_paired(score, phase, "hit", int(top), *vals)
        # This is a unit-test-only counterexample, NEVER a real outcome cohort.
        guarded = assess_reference_score(score)
        self.assertTrue(guarded["all_600_reference_results_present"])
        self.assertEqual(
            guarded["by_phase_mode_topn"]["confirmation"]["hit"]["1"]["net_hit_difference"], 10)
        self.assertTrue(guarded["reference_confirmatory_top5_top10_net_loss_observed"])
        self.assertIn({"mode": "hit", "topn": 5, "net_hit_difference": -5},
                      guarded["reference_confirmatory_regressions"])
        self.assertIn({"mode": "hit", "topn": 10, "net_hit_difference": -5},
                      guarded["reference_confirmatory_regressions"])
        self.assertFalse(guarded["promotion_allowed"])
        self.assertFalse(guarded["model_improvement_proven"])

    def test_nonnegative_topk_observation_still_not_noninferiority_proof(self):
        score = synthetic_reference(full=True)
        for phase in ("pilot", "confirmation"):
            for top, vals in {
                "1": (60, 65, 10, 5),
                "3": (100, 105, 10, 5),
                "5": (150, 150, 10, 10),
                "10": (180, 181, 6, 5),
            }.items():
                set_paired(score, phase, "hit", int(top), *vals)
        guarded = assess_reference_score(score)
        self.assertFalse(guarded["reference_confirmatory_top5_top10_net_loss_observed"])
        self.assertFalse(guarded["promotion_allowed"])
        self.assertFalse(guarded["model_improvement_proven"])

    def test_partial_confirmation_never_declares_regression_pass_or_fail(self):
        score = synthetic_reference(full=True)
        score["confirmed_result_counts"]["confirmation"] = 299
        score["pending_race_codes"] = ["202611091201"]
        for mode in MODES:
            for top in TOPS:
                score["by_phase_mode_topn"]["confirmation"][mode][str(top)][
                    "reference_denominator"] = 299
        guarded = assess_reference_score(score)
        self.assertFalse(guarded["all_600_reference_results_present"])
        self.assertIsNone(guarded["reference_confirmatory_top5_top10_net_loss_observed"])

    def test_nonmonotone_topn_hits_are_rejected(self):
        score = synthetic_reference(full=True)
        set_paired(score, "confirmation", "hit", 1, 5, 5, 0, 0)
        set_paired(score, "confirmation", "hit", 3, 4, 4, 0, 0)
        with self.assertRaisesRegex(ValueError, "nonmonotone_topn_hit_counts"):
            assess_reference_score(score)

    def test_modified_counts_or_forged_certification_are_rejected(self):
        base = synthetic_reference(full=True)
        changed = deepcopy(base)
        set_paired(changed, "confirmation", "hit", 5, 20, 22, 1, 0)
        with self.assertRaisesRegex(ValueError, "paired_counts_inconsistent"):
            assess_reference_score(changed)
        changed = deepcopy(base)
        changed["candidate_first_remote_receipt_verified"] = True
        with self.assertRaisesRegex(ValueError, "reference_must_be_unverified"):
            assess_reference_score(changed)
        changed = deepcopy(base)
        changed["confirmed_result_counts"]["pilot"] = 299
        with self.assertRaisesRegex(ValueError, "missing_duplicate_or_substituted"):
            assess_reference_score(changed)
        changed = deepcopy(base)
        changed["by_phase_mode_topn"]["pilot"]["narrow"]["10"]["candidate"] = 1
        changed["by_phase_mode_topn"]["pilot"]["narrow"]["10"]["gained"] = 1
        with self.assertRaisesRegex(ValueError, "invalid_narrow_top10_alias"):
            assess_reference_score(changed)


if __name__ == "__main__":
    unittest.main()
