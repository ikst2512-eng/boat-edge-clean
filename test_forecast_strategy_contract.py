"""Regression lock: prevent silent scenario-first -> national-rate baseline substitution.

This suite is read-only. It never generates or rewrites any saved prediction.
A legitimate model upgrade must use a separate model identity, preserve the
frozen V2 comparator and pass the independent gates in Issue #1708.
"""
import json
from pathlib import Path
import unittest

from clean_four_modes import rank_modes
from four_mode_archive_api import archived_four_modes
from research_model import probabilities

ROOT = Path(__file__).resolve().parent
POLICY = ROOT / "research" / "forecast_strategy_guard_20261111.json"
FROZEN_RACE = "202611111001"
V2 = "CLEAN_FOUR_MODES_V2_PROVISIONAL_UNCALIBRATED"
COUNTS = {"narrow": 5, "hit": 10, "balance": 16, "hole": 22}


class ForecastStrategyContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = json.loads(POLICY.read_text(encoding="utf-8"))
        cls.frozen = json.loads(
            (ROOT / "four_mode_forecasts" / (FROZEN_RACE + ".json")).read_text(encoding="utf-8")
        )

    def test_original_scenario_first_agreement_is_preserved(self):
        p = self.policy
        self.assertEqual(p["schema"], "BOAT_EDGE_CLEAN_FORECAST_STRATEGY_GUARD_V1")
        self.assertEqual(p["legacy_source_of_truth"]["repository"], "ikst2512-eng/boat-edge")
        self.assertEqual(p["legacy_source_of_truth"]["path"], "data/site_prediction_policy.json")
        self.assertEqual(
            p["requirements_owner"],
            "https://github.com/ikst2512-eng/boat-edge-clean/issues/1708",
        )
        target = p["scenario_first_target"]
        self.assertEqual(len(target["conditional_probability_order"]), 3)
        self.assertEqual(len(target["scenario_worlds"]), 7)
        self.assertIn("second_course_sashi", target["scenario_worlds"])
        self.assertIn("fifth_sixth_beneficiary", target["scenario_worlds"])
        self.assertIn("second_course_escape_assist_and_sashi", target["evidence_fields"])
        self.assertIn("venue_wind_wave_tide", target["evidence_fields"])
        self.assertFalse(target["odds_may_rerank_probabilities"])
        self.assertEqual(target["missing_evidence"], "unknown_or_not_used_not_zero_and_not_claimed_used")
        self.assertEqual(target["status"], "research_only_until_independent_prospective_validation")

    def test_v2_is_explicitly_a_baseline_not_a_scenario_model(self):
        base = self.policy["baseline"]
        self.assertEqual(base["model_version"], V2)
        self.assertEqual(base["modes"], COUNTS)
        self.assertEqual(
            base["inputs_actually_scored"],
            ["six_national_win_rates", "static_1000_race_boat_index_prior"],
        )
        self.assertFalse(base["scenario_awareness"])
        self.assertFalse(base["official_exhibition_actually_consumed"])
        self.assertFalse(base["formally_calibrated"])
        self.assertFalse(base["approved_purchase_decision"])
        self.assertEqual(self.frozen["model_version"], V2)
        self.assertIs(self.frozen["validated"], False)
        self.assertEqual(self.frozen["beforeinfo"], "optional_not_in_snapshot")

    def test_original_v2_board_replays_byte_equivalent_tickets_without_overwrite(self):
        """Use a real immutable 11/11 archive as a regression anchor for V2."""
        f = self.frozen
        self.assertEqual(f["race_code"], FROZEN_RACE)
        rates = f["input_national_win_rates"]
        self.assertEqual(len(rates), 6)
        full_board = probabilities(rates)
        self.assertEqual(len(full_board), 120)
        self.assertAlmostEqual(sum(p for _, p in full_board), 1.0, places=10)
        replay = rank_modes(full_board)
        for mode, count in COUNTS.items():
            with self.subTest(mode=mode):
                original = f["modes"][mode]["tickets"]
                self.assertEqual(len(original), count)
                self.assertEqual(len(replay[mode]["tickets"]), count)
                self.assertEqual(replay[mode]["tickets"], original)
                self.assertIsNone(f["modes"][mode]["actual_hit_rate_pct"])

    def test_site_archive_cannot_upgrade_historical_v2_to_official(self):
        status, data = archived_four_modes(FROZEN_RACE)
        self.assertEqual(status, 200)
        self.assertEqual(data["model_version"], V2)
        self.assertEqual(data["status"], "historical_research_only")
        self.assertIs(data["production_forecast"], False)
        self.assertIs(data["verified_first_git_add"], False)
        self.assertEqual(set(data["modes"]), set(COUNTS))

    def test_capture_cannot_silently_publish_scenario_label_for_v2(self):
        """Any change to V2 generation must explicitly revise and re-review this guard."""
        code = (ROOT / "clean_four_mode_capture.py").read_text(encoding="utf-8")
        self.assertIn("forecast=rank_modes(probabilities(rates))", code)
        self.assertIn('"model_version":"CLEAN_FOUR_MODES_V2_PROVISIONAL_UNCALIBRATED"', code)
        self.assertIn('"input_national_win_rates":rates', code)
        self.assertNotIn('"model_version":"SCENARIO_FORMAL_APPROVED"', code)

    def test_research_promotion_and_preservation_require_proof(self):
        gate = self.policy["promotion_gate"]
        self.assertEqual(gate["pilot_future_races"], 300)
        self.assertEqual(gate["confirmation_future_races"], 300)
        self.assertEqual(gate["compare_top_n"], [1, 3, 5, 10])
        for name in (
            "prior_frozen_forecasts_and_confirmed_outcomes_preserved",
            "registered_separate_model_identity_before_future_cohort",
            "same_race_same_budget_comparison",
            "pre_deadline_verified_full_source_and_actual_model_consumption",
            "independent_remote_first_receipt_verified",
            "do_not_promote_if_top5_or_top10_worsens",
            "human_review_and_public_release_verification_required",
            "no_silent_mode_budget_or_model_substitution",
        ):
            with self.subTest(gate=name):
                self.assertIs(gate[name], True)
        keep = self.policy["do_not_delete_without_independent_reference_audit"]
        self.assertIn("four_mode_forecasts/", keep)
        self.assertIn("research_snapshots/", keep)
        self.assertIn("confirmed_results/", keep)


if __name__ == "__main__":
    unittest.main()
