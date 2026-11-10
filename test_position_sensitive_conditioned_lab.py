"""Synthetic-only invariant and fail-closed tests. No real outcomes are loaded."""
import copy
from itertools import permutations
import math
import unittest

from position_sensitive_conditioned_lab import experimental_conditional_board, inspect_feature_readiness


def baseline():
    raw = [(t, 7-t[0] + (t[1] / 20)) for t in permutations(range(1, 7), 3)]
    total = sum(p for _, p in raw)
    return [(t, p/total) for t, p in raw]


def evidence():
    return {
        "boats": [
            {"boat": i, "motor_2ren_pct": 50 if i != 2 else 85,
             "entry_course": i, "local_win_rate": 5 + i / 4,
             "average_st_s": .10 + i / 100,
             "exhibition_st_s": .05 + i / 100,
             "exhibition_time_s": 6.7 + i / 100}
            for i in range(1, 7)
        ],
        "context": {"wind_speed_mps": 3, "wind_from_true_deg": 60,
                    "start_heading_true_deg": 60, "wave_height_cm": 4},
    }


class ConditionalLabTests(unittest.TestCase):
    def run_lab(self, features=None, params=None, b=None):
        if params is None:
            params = {"motor_2ren_pct": {"second": .7, "third": .3}}
        return experimental_conditional_board(
            baseline() if b is None else b,
            evidence() if features is None else features, params,
            "EXPLORATORY_ONLY_feature_gate_20261109")

    def test_all_120_and_every_head_mass_preserved(self):
        b = baseline()
        out = self.run_lab(params={
            "motor_2ren_pct": {"second": .7, "third": .2},
            "average_st_s": {"second": .1, "third": .05},
            "entry_course": {"second": .12, "third": .05},
            "headwind_x_entry": {"second": .1, "third": .05},
            "wave_x_entry": {"second": .02, "third": .01},
        })
        self.assertEqual(len(out["ranked_board"]), 120)
        actual = dict(out["ranked_board"])
        self.assertEqual(len(actual), 120)
        self.assertAlmostEqual(sum(actual.values()), 1, places=12)
        for h in range(1, 7):
            self.assertAlmostEqual(
                sum(p for t, p in b if t[0] == h),
                sum(p for t, p in actual.items() if t[0] == h), places=12)
        self.assertFalse(out["formal"])
        self.assertFalse(out["promotion_allowed"])
        self.assertFalse(out["model_improvement_proven"])
        self.assertFalse(out["calibrated_probabilities"])
        self.assertFalse(out["confirmed_results_read"])

    def test_conditional_rank_changes_from_supplied_feature_not_forced_diversity(self):
        params = {"motor_2ren_pct": {"second": 1, "third": .1}}
        first = dict(self.run_lab(params=params)["ranked_board"])
        changed = evidence()
        changed["boats"][1]["motor_2ren_pct"] = 20
        changed["boats"][2]["motor_2ren_pct"] = 90
        second = dict(self.run_lab(features=changed, params=params)["ranked_board"])
        self.assertGreater(first[(1,2,3)], first[(1,3,2)])
        self.assertLess(second[(1,2,3)], second[(1,3,2)])

    def test_real_exhibition_seconds_accepted_but_fabricated_47_seconds_rejected(self):
        good = self.run_lab(params={"exhibition_time_s": {"second": .3, "third": .15}})
        self.assertIn("exhibition_time_s", good["active_features"])
        self.assertEqual(len(good["ranked_board"]), 120)
        data = evidence()
        data["boats"][0]["exhibition_time_s"] = 47.1
        with self.assertRaisesRegex(ValueError, "invalid_exhibition_time_s"):
            self.run_lab(features=data, params={
                "exhibition_time_s": {"second": .3, "third": .15}})
        self.assertFalse(good["formal"])
        self.assertFalse(good["model_improvement_proven"])

    def test_zero_weight_does_not_impute_missing_inputs(self):
        blank = {"boats": [{"boat": i} for i in range(1, 7)], "context": {}}
        result = self.run_lab(features=blank,
            params={"exhibition_st_s": {"second": 0., "third": 0.}})
        for ticket, p in baseline():
            self.assertAlmostEqual(dict(result["ranked_board"])[ticket], p, places=14)
        self.assertEqual(result["active_features"], [])

    def test_missing_active_field_is_rejected(self):
        data = evidence()
        del data["boats"][4]["motor_2ren_pct"]
        with self.assertRaisesRegex(ValueError, "invalid_motor_2ren_pct"):
            self.run_lab(features=data)

    def test_partial_or_duplicate_six_boat_inputs_rejected(self):
        for operation in ("remove", "duplicate"):
            data = evidence()
            if operation == "remove":
                data["boats"].pop()
            else:
                data["boats"][5]["boat"] = 1
            with self.assertRaises(ValueError):
                self.run_lab(features=data)

    def test_entry_must_be_permutation_if_used(self):
        data = evidence()
        data["boats"][4]["entry_course"] = 1
        with self.assertRaisesRegex(ValueError, "entry_course_not_permutation"):
            self.run_lab(features=data, params={
                "entry_course": {"second": .1, "third": .1}})

    def test_wind_requires_grounded_bearing_not_guess(self):
        data = evidence()
        del data["context"]["start_heading_true_deg"]
        with self.assertRaisesRegex(ValueError, "invalid_start_heading"):
            self.run_lab(features=data, params={
                "headwind_x_entry": {"second": .1, "third": .1}})

    def test_no_result_or_unapproved_fields_accepted(self):
        data = evidence()
        data["confirmed_finish"] = "1-2-3"
        with self.assertRaisesRegex(ValueError, "outcome_contaminated"):
            self.run_lab(features=data)
        data = evidence()
        data["boats"][0]["payout"] = 999
        with self.assertRaisesRegex(ValueError, "invalid_boat_fields"):
            self.run_lab(features=data)

    def test_rejects_bad_baseline_or_forged_parameter(self):
        b = baseline()
        b[1] = b[0]
        with self.assertRaisesRegex(ValueError, "duplicate_baseline_ticket"):
            self.run_lab(b=b)
        with self.assertRaisesRegex(ValueError, "new_study_identity"):
            experimental_conditional_board(baseline(), evidence(),
                {"motor_2ren_pct": {"second": 1, "third": 0}}, "1698")
        with self.assertRaisesRegex(ValueError, "unregistered_feature_name"):
            self.run_lab(params={"magical_win": {"second": 1, "third": 1}})
        with self.assertRaisesRegex(ValueError, "invalid_coefficient"):
            self.run_lab(params={"motor_2ren_pct": {"second": math.nan, "third": 0}})

    def test_same_race_topk_nested_and_deterministic(self):
        a = self.run_lab()
        b = self.run_lab()
        self.assertEqual(a, b)
        ordered = [t for t, p in a["ranked_board"]]
        self.assertEqual(ordered[:1], ordered[:3][:1])
        self.assertEqual(ordered[:3], ordered[:5][:3])
        self.assertEqual(ordered[:5], ordered[:10][:5])
        self.assertTrue(a["requires_independent_new_preregistration"])


    def test_available_vs_missing_evidence_does_not_impute(self):
        data = evidence()
        del data["boats"][5]["exhibition_st_s"]
        del data["context"]["start_heading_true_deg"]
        status = inspect_feature_readiness(data)
        self.assertIn("motor_2ren_pct", status["structurally_present_features"])
        self.assertIn("local_win_rate", status["structurally_present_features"])
        self.assertIn("exhibition_st_s", status["missing_or_invalid_features"])
        self.assertIn("headwind_x_entry", status["missing_or_invalid_features"])
        self.assertNotIn("wave_x_entry", status["missing_or_invalid_features"])
        self.assertFalse(status["feature_values_imputed"])
        self.assertFalse(status["official_bytes_and_predeadline_receipts_verified"])
        self.assertFalse(status["formal"])
        data["confirmed_finish"] = "1-2-3"
        with self.assertRaisesRegex(ValueError, "outcome_contaminated"):
            inspect_feature_readiness(data)


if __name__ == "__main__":
    unittest.main()
