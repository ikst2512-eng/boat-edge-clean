"""Mathematical conditional decomposition invariants, synthetic only."""
import copy
import unittest

from research_model import probabilities
from four_mode_position_sensitive_shadow import shadow_probabilities
from position_sensitive_conditioned_lab import experimental_conditional_board
from position_sensitive_conditional_decomposition import compare_conditional_decomposition
from test_position_sensitive_conditioned_lab import evidence

RATES = [6.2, 5.4, 7.1, 5.8, 6.9, 4.8]


class ConditionalDecompositionTests(unittest.TestCase):
    def before_after(self):
        frozen = shadow_probabilities(RATES)
        candidate = experimental_conditional_board(
            frozen, evidence(), {
                "motor_2ren_pct": {"second": 1.0, "third": .25},
                "exhibition_st_s": {"second": .2, "third": .1},
            }, "EXPLORATORY_ONLY_SEQUENTIAL_DECOMPOSITION_20261109")
        return frozen, candidate["ranked_board"]

    def test_exact_sequential_identity_and_all_six_heads(self):
        b, a = self.before_after()
        report = compare_conditional_decomposition(b, a)
        self.assertEqual(len(report["second_given_head"]), 6)
        self.assertEqual(len(report["third_given_head_and_second"]), 30)
        self.assertTrue(report["head_mass_preserved_for_all_six"])
        self.assertGreater(report["max_abs_second_probability_delta"], 0)
        self.assertGreater(report["max_abs_third_probability_delta"], 0)
        for head in report["second_given_head"].values():
            self.assertAlmostEqual(sum(head["second_probabilities_before"].values()), 1)
            self.assertAlmostEqual(sum(head["second_probabilities_after"].values()), 1)
        for pair in report["third_given_head_and_second"].values():
            self.assertAlmostEqual(sum(pair["third_probabilities_before"].values()), 1)
            self.assertAlmostEqual(sum(pair["third_probabilities_after"].values()), 1)
        for name in ("outcome_accuracy_measured", "inputs_official_and_predeadline_verified",
                     "model_improvement_proven", "formal", "promotion_allowed",
                     "production_changed"):
            self.assertFalse(report[name], name)

    def test_same_board_does_not_force_rank_change(self):
        b = shadow_probabilities(RATES)
        result = compare_conditional_decomposition(b, b)
        self.assertEqual(result["heads_with_top_second_changed"], 0)
        self.assertEqual(result["head_second_pairs_with_top_third_changed"], 0)
        self.assertEqual(result["max_abs_second_probability_delta"], 0)
        self.assertEqual(result["max_abs_third_probability_delta"], 0)

    def test_reject_modified_first_mass_even_when_global_normalized(self):
        b = shadow_probabilities(RATES)
        vals = dict(b)
        small = min(vals[(1, 2, 3)], vals[(2, 1, 3)]) / 10
        vals[(1, 2, 3)] += small
        vals[(2, 1, 3)] -= small
        with self.assertRaisesRegex(ValueError, "first_boat_probability_mass_drift"):
            compare_conditional_decomposition(b, list(vals.items()))

    def test_reject_duplicate_ticket_or_partial_board(self):
        b = shadow_probabilities(RATES)
        with self.assertRaisesRegex(ValueError, "duplicate_baseline_ticket"):
            compare_conditional_decomposition(b, b[:-1] + [b[0]])
        with self.assertRaisesRegex(ValueError, "incomplete_baseline_board"):
            compare_conditional_decomposition(b[:-1], b)


if __name__ == "__main__":
    unittest.main()
