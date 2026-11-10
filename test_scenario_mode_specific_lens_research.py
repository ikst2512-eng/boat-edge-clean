"""Synthetic-only mode-specific scenario lens, never official outcome evidence."""
import copy
import unittest

from research_model import probabilities
from scenario_first_head_research import hypothetical_head_board
from scenario_mode_specific_lens_research import (
    compare_mode_specific_lenses, MODES, BUDGETS,
)

ID = "EXPLORATORY_ONLY_MODE_SPECIFIC_PAIR_SCENARIOS_20261110"
RATES = [5.4, 6.0, 6.5, 6.1, 5.9, 5.1]


def fixtures():
    base = probabilities(RATES)
    shifts = {
        "escape_wall": [4, 0, 0, 0, 0, 0],
        "two_sashi": [-1, 4, 0, 0, 0, 0],
        "third_attack": [-1, 0, 4, 0, 0, 0],
        "outer_benefit": [-1, 0, 0, 0, 4, 0],
    }
    boards = {
        key: hypothetical_head_board(
            base, vec, study_id="EXPLORATORY_ONLY_SYNTHETIC_"+key.upper()
        )["ranked_board"] for key, vec in shifts.items()
    }
    names = tuple(sorted(boards))
    def w(**entries):
        return {key: entries.get(key, 0.0) for key in names}
    weights = {
        "narrow": w(escape_wall=1.0),
        "hit": w(two_sashi=1.0),
        "balance": w(escape_wall=0.5, third_attack=0.5),
        "hole": w(third_attack=0.5, outer_benefit=0.5),
    }
    return boards, weights


class ModeSpecificLensTests(unittest.TestCase):
    def test_all_four_modes_valid_counts_and_no_promotion(self):
        boards, weights = fixtures()
        before = copy.deepcopy((boards, weights))
        r = compare_mode_specific_lenses(boards, weights, study_id=ID)
        self.assertEqual(set(r["four_modes"]), set(MODES))
        self.assertEqual({m: len(x["tickets"]) for m, x in r["four_modes"].items()},
                         BUDGETS)
        self.assertEqual(len(r["pairwise_overlap_diagnostics"]), 6)
        self.assertEqual((boards, weights), before)
        for flag in ("formal", "forecast_usable", "betting_recommendation",
                     "production_changed", "promotion_allowed",
                     "source_scenario_board_origin_authenticated",
                     "official_beforeinfo_exhibition_and_odds120_verified",
                     "candidate_first_remote_pre_t12_receipt_verified",
                     "coefficient_calibration_or_hit_rate_proven",
                     "wind_tide_motor_entry_or_wall_measured_from_official_source"):
            self.assertFalse(r[flag], flag)
        self.assertFalse(r["payout_or_finish_read_by_this_function"])

    def test_shifts_cause_conditional_scenario_difference_not_forced(self):
        boards, weights = fixtures()
        r = compare_mode_specific_lenses(boards, weights, study_id=ID)
        self.assertGreater(r["distinct_top1_mode_tickets"], 1)
        self.assertNotEqual(r["four_modes"]["narrow"]["mixture_sha256"],
                            r["four_modes"]["hit"]["mixture_sha256"])
        self.assertNotEqual(r["four_modes"]["narrow"]["top1"],
                            r["four_modes"]["hit"]["top1"])
        self.assertFalse(r["pairwise_overlap_diagnostics"]["narrow__hit"]["forced_nonoverlap"])

    def test_identical_weights_no_fabricated_difference(self):
        boards, weights = fixtures()
        same = {mode: copy.deepcopy(weights["narrow"]) for mode in MODES}
        r = compare_mode_specific_lenses(boards, same, study_id=ID)
        self.assertEqual(
            r["four_modes"]["narrow"]["top1"], r["four_modes"]["hit"]["top1"])
        self.assertEqual(
            r["pairwise_overlap_diagnostics"]["narrow__hit"]["shared_tickets"], 5)
        self.assertEqual(
            r["pairwise_overlap_diagnostics"]["narrow__hit"]["share_of_smaller_mode"], 1)
        self.assertEqual(
            len({x["mixture_sha256"] for x in r["four_modes"].values()}), 1)

    def test_different_weights_but_same_scenario_board_cannot_manufacture_change(self):
        boards, weights = fixtures()
        base = copy.deepcopy(boards["escape_wall"])
        boards = {key: copy.deepcopy(base) for key in boards}
        r = compare_mode_specific_lenses(boards, weights, study_id=ID)
        self.assertEqual(
            len({x["mixture_sha256"] for x in r["four_modes"].values()}), 1)
        self.assertEqual(r["distinct_top1_mode_tickets"], 2)
        # The other slot is the existing hole rank-11 selector, not a forced
        # distinct top1 for narrow/hit/balance.
        for mode in ("narrow", "hit", "balance"):
            self.assertEqual(r["four_modes"]["narrow"]["top1"],
                             r["four_modes"][mode]["top1"])

    def test_missing_mode_or_malformed_study_id_fails(self):
        boards, weights = fixtures()
        del weights["balance"]
        with self.assertRaisesRegex(ValueError, "mode_specific_study"):
            compare_mode_specific_lenses(boards, weights, study_id=ID)
        boards, weights = fixtures()
        with self.assertRaisesRegex(ValueError, "mode_specific_study"):
            compare_mode_specific_lenses(boards, weights, study_id="LIVE_PRODUCTION")

    def test_missing_scenario_weight_fails_without_fallback(self):
        boards, weights = fixtures()
        del weights["hole"]["two_sashi"]
        with self.assertRaisesRegex(ValueError, "scenario_weights_missing_or_extra"):
            compare_mode_specific_lenses(boards, weights, study_id=ID)

    def test_weight_normalization_fails(self):
        boards, weights = fixtures()
        weights["narrow"]["escape_wall"] = .8
        with self.assertRaisesRegex(ValueError, "scenario_weights_must_sum_one"):
            compare_mode_specific_lenses(boards, weights, study_id=ID)

    def test_unknown_outcome_scenario_rejected(self):
        boards, weights = fixtures()
        boards["winning_ticket"] = boards["escape_wall"]
        for mode in MODES:
            weights[mode]["winning_ticket"] = 0
        with self.assertRaisesRegex(ValueError, "scenario_name_or_weight_mismatch"):
            compare_mode_specific_lenses(boards, weights, study_id=ID)

    def test_corrupt_120_board_rejected(self):
        boards, weights = fixtures()
        boards["escape_wall"] = boards["escape_wall"][:119]
        with self.assertRaisesRegex(ValueError, "full_120_scenario_board_required"):
            compare_mode_specific_lenses(boards, weights, study_id=ID)

    def test_nested_mode_still_possible_and_never_penalized(self):
        boards, weights = fixtures()
        r = compare_mode_specific_lenses(boards, weights, study_id=ID)
        for row in r["pairwise_overlap_diagnostics"].values():
            self.assertGreaterEqual(row["shared_tickets"], 0)
            self.assertLessEqual(row["share_of_smaller_mode"], 1)
            self.assertFalse(row["forced_nonoverlap"])
        self.assertTrue(r["different_modes_are_NOT_required_to_have_different_tickets"])


if __name__ == "__main__":
    unittest.main()
