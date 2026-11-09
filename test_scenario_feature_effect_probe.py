"""Check unused vs genuinely score-changing feature hypotheses (not accuracy)."""
import copy
import unittest

from research_model import probabilities
from scenario_feature_effect_probe import probe_feature_effects
from scenario_first_head_research import hypothetical_head_board
from scenario_four_mode_bridge import compose_scenario_research


def emit_with_research_hypotheses(state):
    baseline = probabilities(state["national_win_rates"])
    # Synthetic-only engineering hypothesis, not an official/empirical wind
    # or tide coefficient. 'tide_height_cm' is supplied but not used.
    score = float(state["wind_speed_mps"])
    head = hypothetical_head_board(
        baseline,
        [score / 3.0, 0, -score / 3.0, 0, 0, 0],
        study_id="EXPLORATORY_ONLY_ABLATION_FIXTURE")
    return compose_scenario_research(
        {"escape_wall": head["ranked_board"]},
        {"escape_wall": 1.0}
    )


class FeatureEffectTests(unittest.TestCase):
    def setUp(self):
        self.base = {
            "national_win_rates": [5, 6, 6.5, 4.2, 5.2, 5.4],
            "wind_speed_mps": 2.0,
            "tide_height_cm": 110.0
        }

    def test_detect_changes_and_unused_supplied_tide(self):
        original = copy.deepcopy(self.base)
        result = probe_feature_effects(self.base, {
            "wind_speed_mps": 6.0,
            "tide_height_cm": 180.0,
        }, emit_with_research_hypotheses)
        self.assertTrue(result["tested_hypotheses"]["wind_speed_mps"]["full_120_board_changed"])
        self.assertFalse(result["tested_hypotheses"]["tide_height_cm"]["full_120_board_changed"])
        self.assertFalse(result["tested_hypotheses"]["tide_height_cm"]["actual_official_feature_used_verified"])
        self.assertFalse(result["official_t12_certified"])
        self.assertEqual(self.base, original)
        self.assertFalse(result["promotion_allowed"])
        self.assertIsNone(result["confirmed_results_read"])
        self.assertFalse(result["external_emitter_result_blind_independently_verified"])

    def test_same_value_and_missing_variant_rejected(self):
        for variants in [{"wind_speed_mps": 2.0},
                         {"wave_height_cm": 2.0},
                         {"finish_order": "1-2-3"}, {}]:
            with self.subTest(variants=variants):
                with self.assertRaises(ValueError):
                    probe_feature_effects(self.base, variants, emit_with_research_hypotheses)

    def test_outcome_and_nonfinite_features_rejected(self):
        for data in [
            dict(self.base, result="1-2-3"),
            dict(self.base, payout=100),
            dict(self.base, post_race_weather={"wind_speed_mps": 7}),
            dict(self.base, wind_speed_mps=float("nan"))
        ]:
            with self.subTest(data=data):
                with self.assertRaises(ValueError):
                    probe_feature_effects(
                        data, {"wind_speed_mps": 5}, emit_with_research_hypotheses)

    def test_reject_fake_formal_emitter(self):
        def bad(state):
            result = emit_with_research_hypotheses(state)
            result["formal"] = True
            return result
        with self.assertRaises(ValueError):
            probe_feature_effects(self.base, {"wind_speed_mps": 5.0}, bad)

    def test_refuses_incomplete_research_emitter(self):
        with self.assertRaises(ValueError):
            probe_feature_effects(
                self.base, {"wind_speed_mps": 5.0},
                lambda _: {"formal": False})

    def test_rejects_unsupported_field_in_baseline(self):
        with self.assertRaises(ValueError):
            probe_feature_effects(
                dict(self.base, arbitrary_unverified_feature=2),
                {"wind_speed_mps": 5.0},
                emit_with_research_hypotheses)


if __name__ == "__main__":
    unittest.main()
