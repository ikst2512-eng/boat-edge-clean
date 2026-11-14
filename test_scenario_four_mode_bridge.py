"""Negative and structural tests for the isolated #1708 scenario bridge."""
import copy
import math
import unittest
from itertools import permutations

from scenario_four_mode_bridge import compose_scenario_research

TICKETS = list(permutations(range(1, 7), 3))


def scenario_board(first, second=2):
    raw = [
        (ticket, (40.0 if ticket[0] == first else 1.0)
         * (3.0 if ticket[1] == second else 1.0))
        for ticket in TICKETS
    ]
    total = sum(value for _, value in raw)
    return [(t, value / total) for t, value in raw]


class ScenarioBridgeTests(unittest.TestCase):
    def setUp(self):
        self.boards = {
            "escape_wall": scenario_board(1),
            "third_attack": scenario_board(3),
            "outer_benefit": scenario_board(5),
        }
        self.weights = {"escape_wall": 0.3,
                        "third_attack": 0.4, "outer_benefit": 0.3}

    def test_all_four_modes_from_same_scenario_mixture(self):
        out = compose_scenario_research(self.boards, self.weights)
        modes = out["existing_four_mode_selector_on_mixture"]
        self.assertEqual(
            {key: len(value["tickets"]) for key, value in modes.items()},
            {"narrow": 5, "hit": 10, "balance": 16, "hole": 22})
        self.assertEqual(
            [r["combo"] for r in modes["narrow"]["tickets"]],
            [r["combo"] for r in modes["hit"]["tickets"][:5]])
        self.assertEqual(len(out["top10_reference"]), 10)
        self.assertFalse(out["formal"])
        self.assertFalse(out["forecast_usable"])
        self.assertFalse(out["promotion_allowed"])
        self.assertFalse(out["probabilities_calibrated"])

    def test_scenario_weights_cause_input_sensitivity_not_forced_diversity(self):
        a = compose_scenario_research(
            {"escape_wall": scenario_board(1)}, {"escape_wall": 1.0})
        b = compose_scenario_research(
            {"third_attack": scenario_board(3)}, {"third_attack": 1.0})
        self.assertEqual(a["top10_reference"][0]["combo"][0], "1")
        self.assertEqual(b["top10_reference"][0]["combo"][0], "3")
        self.assertNotEqual(
            a["top10_reference"][0]["combo"],
            b["top10_reference"][0]["combo"])

    def test_scenario_supported_hole_excludes_normal_top_ten(self):
        out = compose_scenario_research(self.boards, self.weights)
        normal = {r["combo"] for r in out["top10_reference"]}
        hole = out["separate_scenario_hole_research"]
        self.assertEqual(hole["status"], "hypothesis_candidates")
        self.assertEqual(len(hole["tickets"]), 22)
        self.assertTrue(all(r["combo"] not in normal for r in hole["tickets"]))
        self.assertTrue(all(r["scenario"] in
                            {"third_attack", "fourth_cado", "outer_benefit"}
                            for r in hole["tickets"]))
        self.assertFalse(hole["expected_value_claim"])

    def test_no_attack_scenario_does_not_fabricate_hole(self):
        out = compose_scenario_research(
            {"escape_wall": scenario_board(1)}, {"escape_wall": 1})
        hole = out["separate_scenario_hole_research"]
        self.assertEqual(hole["status"], "unavailable_no_attack_or_benefit_scenario")
        self.assertEqual(hole["tickets"], [])
        self.assertEqual(len(out["existing_four_mode_selector_on_mixture"]["hole"]["tickets"]), 22)

    def test_repeatable_and_immutable(self):
        before = copy.deepcopy(self.boards)
        first = compose_scenario_research(self.boards, self.weights)
        second = compose_scenario_research(self.boards, self.weights)
        self.assertEqual(first, second)
        self.assertEqual(self.boards, before)
        self.assertEqual(len(first["scenario_board_sha256"]["escape_wall"]), 64)
        self.assertFalse(first["source_feature_provenance_independently_verified"])
        self.assertFalse(first["verified_official_six_exhibition_and_120_odds"])

    def test_invalid_missing_scenario_and_implicit_weights_rejected(self):
        for boards, weights in [
            ({}, {}),
            ({"escape_wall": scenario_board(1)}, {}),
            (self.boards, {"escape_wall": 1.0}),
            ({"result": scenario_board(1)}, {"result": 1.0}),
            ({"escape_wall": scenario_board(1)}, {"escape_wall": 0.99}),
            ({"escape_wall": scenario_board(1)}, {"escape_wall": True}),
            ({"escape_wall": scenario_board(1)}, {"escape_wall": float("nan")}),
        ]:
            with self.subTest(weights=weights):
                with self.assertRaises(ValueError):
                    compose_scenario_research(boards, weights)

    def test_incomplete_duplicate_and_nonfinite_probability_rejected(self):
        valid = scenario_board(1)
        bads = [
            valid[:119],
            [(valid[0][0], valid[0][1])] + valid[:119],
            [(valid[0][0], math.inf)] + valid[1:],
            [(valid[0][0], -0.1)] + valid[1:],
            [(valid[0][0], 0.0)] + valid[1:],
            [((1, 1, 2), valid[0][1])] + valid[1:],
            [((1, 2, 7), valid[0][1])] + valid[1:],
        ]
        for invalid in bads:
            with self.subTest(length=len(invalid)):
                with self.assertRaises(ValueError):
                    compose_scenario_research({"escape_wall": invalid},
                                              {"escape_wall": 1})

    def test_tickets_mixture_is_bounded_and_unique(self):
        out = compose_scenario_research(self.boards, self.weights)
        for rows in out["existing_four_mode_selector_on_mixture"].values():
            tickets = rows["tickets"]
            self.assertEqual(len({r["combo"] for r in tickets}), len(tickets))
            self.assertTrue(all(0 <= r["p"] <= 100 for r in tickets))
        self.assertFalse(out["confirmed_results_read"])
        self.assertFalse(out["betting_recommendation"])
        self.assertFalse(out["production_changed"])


if __name__ == "__main__":
    unittest.main()
