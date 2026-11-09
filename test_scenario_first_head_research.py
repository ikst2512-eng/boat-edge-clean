"""Safety and sensitivity checks for a separate research first-head step."""
import copy
import math
import unittest
from itertools import permutations

from research_model import probabilities
from scenario_first_head_research import hypothetical_head_board
from scenario_four_mode_bridge import compose_scenario_research

class FirstHeadResearchTests(unittest.TestCase):
    def setUp(self):
        self.baseline = probabilities([4.5, 6.8, 5.3, 4.9, 5.9, 5.2])
        self.identity = "EXPLORATORY_ONLY_HEAD_SCENARIO_1708"

    def test_zero_hypothesis_preserves_all_120_probabilities(self):
        result = hypothetical_head_board(
            self.baseline, [0, 0, 0, 0, 0, 0], study_id=self.identity)
        original = dict(self.baseline)
        for ticket, prob in result["ranked_board"]:
            self.assertAlmostEqual(prob, original[ticket], places=12)
        self.assertEqual(len(result["ranked_board"]), 120)
        self.assertFalse(result["official_wind_tide_entry_used"])

    def test_shift_changes_head_mass_not_second_third_given_head(self):
        altered = hypothetical_head_board(
            self.baseline, [-2, 0, 2, 0, 0, 0], study_id=self.identity)
        scores = dict(altered["ranked_board"])
        original = dict(self.baseline)
        old_mass = altered["original_first_mass"]
        new_mass = altered["hypothesis_first_mass"]
        self.assertGreater(new_mass["3"], old_mass["3"])
        self.assertLess(new_mass["1"], old_mass["1"])
        for h in range(1, 7):
            for ticket in permutations(range(1, 7), 3):
                if ticket[0] == h:
                    self.assertAlmostEqual(
                        scores[ticket] / new_mass[str(h)],
                        original[ticket] / old_mass[str(h)], places=12)
        self.assertAlmostEqual(sum(scores.values()), 1.0, places=12)

    def test_scenarios_feed_all_modes_without_frozen_selector_change(self):
        prior = copy.deepcopy(self.baseline)
        a = hypothetical_head_board(self.baseline,
                                    [1, 0, 0, 0, 0, 0], study_id=self.identity)
        b = hypothetical_head_board(self.baseline,
                                    [-1, 0, 2, 0, 0, 0], study_id=self.identity)
        mixed = compose_scenario_research(
            {"escape_wall": a["ranked_board"],
             "third_attack": b["ranked_board"]},
            {"escape_wall": .4, "third_attack": .6})
        self.assertEqual(len(mixed["top10_reference"]), 10)
        self.assertEqual(len(mixed["existing_four_mode_selector_on_mixture"]["balance"]["tickets"]), 16)
        self.assertEqual(self.baseline, prior)
        self.assertFalse(mixed["formal"])
        self.assertFalse(b["promotion_allowed"])

    def test_bad_scores_and_identity_fail_closed(self):
        for scores in [
            [], [0] * 5, [0] * 7, [0] * 5 + [float("nan")],
            [0] * 5 + [float("inf")], [0] * 5 + [7],
            [0] * 5 + [True], [0] * 5 + ["0"], {1: 0}
        ]:
            with self.subTest(scores=scores):
                with self.assertRaises(ValueError):
                    hypothetical_head_board(self.baseline, scores,
                                            study_id=self.identity)
        for bad_id in ["SHADOW_1698", "", None, "EXPLORATORY_ONLY_" + "x" * 101]:
            with self.assertRaises(ValueError):
                hypothetical_head_board(self.baseline, [0]*6, study_id=bad_id)

    def test_bad_board_rejected(self):
        invalid = self.baseline[:]
        invalid[0] = (invalid[0][0], -0.2)
        with self.assertRaises(ValueError):
            hypothetical_head_board(invalid, [0]*6, study_id=self.identity)

    def test_no_results_or_official_claim(self):
        result = hypothetical_head_board(self.baseline, [0]*6,
                                         study_id=self.identity)
        for field in ("formal", "calibrated", "first_remote_receipt_verified",
                      "result_read", "production_changed", "promotion_allowed"):
            self.assertFalse(result[field])


if __name__ == "__main__":
    unittest.main()
