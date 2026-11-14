"""Pinned #1698 integration tests, not a copy of its conditional model.

The PR-only workflow fetches exactly the reviewed #1698 commit and exports
that file in PYTHONPATH. Local runs without that dependency are skipped.
No actual official HTTP requests, model deployment or results are involved.
"""
import copy
import hashlib
import importlib
import json
import os
import unittest

from scenario_official_exhibition_projection import project_exhibition_research
from scenario_exhibition_all_mode_runner import run_exhibition_scenario_lab
from scenario_first_head_research import hypothetical_head_board
from test_scenario_official_exhibition_projection import fixture, replay_stub


class PinnedConditionalIntegrationTests(unittest.TestCase):
    def setUp(self):
        if os.environ.get("RESEARCH_1698_PIN_REQUIRED") != "1":
            self.skipTest("Requires pinned #1698 Git blob; no unpinned fallback")
        try:
            m = importlib.import_module("position_sensitive_conditioned_lab")
        except ImportError as exc:
            self.fail("Pinned #1698 conditional lab not available: " + str(exc))
        self.condition = m.experimental_conditional_board
        source, candidate = fixture()  # Explicit mock; never official
        self.projection = project_exhibition_research(
            source, candidate, replay_stub)
        self.rates = [5.2, 5.9, 6.4, 4.7, 5.5, 5.1]
        self.plans = {
            "escape_wall": {
                "weight": .45,
                "head_log_shifts": [1.4, 0, 0, 0, 0, 0],
                "position_coefficients": {
                    "exhibition_st_s": {"second": .30, "third": .15},
                    "exhibition_time_s": {"second": .20, "third": .10},
                },
            },
            "third_attack": {
                "weight": .35,
                "head_log_shifts": [-.4, 0, 1.8, 0, 0, 0],
                "position_coefficients": {
                    "exhibition_st_s": {"second": .55, "third": .28},
                    "exhibition_time_s": {"second": .30, "third": .15},
                },
            },
            "outer_benefit": {
                "weight": .20,
                "head_log_shifts": [0, 0, 0, 0, 1.2, .8],
                "position_coefficients": {
                    "exhibition_st_s": {"second": .25, "third": .20},
                    "exhibition_time_s": {"second": .15, "third": .10},
                },
            },
        }
        self.identity = "EXPLORATORY_ONLY_SCENARIO_1710_INTEGRATION"

    def run_lab(self, projection=None, plans=None, callback=None):
        return run_exhibition_scenario_lab(
            self.projection if projection is None else projection,
            self.rates,
            self.plans if plans is None else plans,
            self.condition if callback is None else callback,
            study_id=self.identity)

    def test_real_1698_conditional_model_executes_all_four_modes(self):
        before = copy.deepcopy((self.projection, self.plans, self.rates))
        result = self.run_lab()
        self.assertEqual(result["race_code"], "202611091710")
        self.assertEqual(set(result["mode_result"]["existing_four_mode_selector_on_mixture"]),
                         {"narrow", "hit", "balance", "hole"})
        self.assertEqual(
            {mode: len(data["tickets"]) for mode, data in
             result["mode_result"]["existing_four_mode_selector_on_mixture"].items()},
            {"narrow": 5, "hit": 10, "balance": 16, "hole": 22})
        self.assertEqual(len(result["mode_result"]["top10_reference"]), 10)
        self.assertEqual(
            len(result["mode_result"]["separate_scenario_hole_research"]["tickets"]),
            22)
        self.assertEqual((self.projection, self.plans, self.rates), before)
        self.assertFalse(result["actual_entry_wind_tide_motor_or_wall_used"])
        self.assertFalse(result["forecast_usable"])
        self.assertFalse(result["formal"])
        self.assertFalse(result["production_changed"])
        self.assertFalse(result["promotion_allowed"])

    def test_exhibition_ST_affects_board_when_synthetically_varied(self):
        original = self.run_lab()
        changed = copy.deepcopy(self.projection)
        changed["exhibition_features_by_boat"][2]["exhibition_st_s"] = .01
        with self.assertRaises(ValueError):
            self.run_lab(projection=changed)  # Cannot reuse old SHA.
        changed["exhibition_features_sha256"] = hashlib.sha256(
            json.dumps(changed["exhibition_features_by_boat"], sort_keys=True,
                       separators=(",", ":"), ensure_ascii=False
                      ).encode("utf-8")
        ).hexdigest()
        after = self.run_lab(projection=changed)
        self.assertNotEqual(original["mode_result"]["mixed_120_board_sha256"],
                            after["mode_result"]["mixed_120_board_sha256"])
        # A self-recalculated synthetic SHA is NOT a primary source receipt.
        self.assertFalse(after["actual_official_exhibition_consumption_independently_replayed"])

    def test_real_second_exhibition_time_changes_board_when_enabled(self):
        original = self.run_lab()
        changed = copy.deepcopy(self.projection)
        changed["exhibition_features_by_boat"][0]["exhibition_time_s"] = 7.05
        changed["exhibition_features_sha256"] = hashlib.sha256(
            json.dumps(changed["exhibition_features_by_boat"], sort_keys=True,
                       separators=(",", ":"), ensure_ascii=False
                       ).encode("utf-8")
        ).hexdigest()
        after = self.run_lab(projection=changed)
        self.assertNotEqual(original["mode_result"]["mixed_120_board_sha256"],
                            after["mode_result"]["mixed_120_board_sha256"])
        self.assertFalse(after["actual_official_exhibition_consumption_independently_replayed"])

    def test_exhibition_time_when_coefficients_zero_does_not_change_board(self):
        plans = copy.deepcopy(self.plans)
        for plan in plans.values():
            plan["position_coefficients"]["exhibition_time_s"] = {
                "second": 0.0, "third": 0.0}
        original = self.run_lab(plans=plans)
        changed = copy.deepcopy(self.projection)
        changed["exhibition_features_by_boat"][0]["exhibition_time_s"] = 7.05
        changed["exhibition_features_sha256"] = hashlib.sha256(
            json.dumps(changed["exhibition_features_by_boat"], sort_keys=True,
                       separators=(",", ":"), ensure_ascii=False
                      ).encode("utf-8")
        ).hexdigest()
        after = self.run_lab(projection=changed, plans=plans)
        self.assertEqual(original["mode_result"]["mixed_120_board_sha256"],
                         after["mode_result"]["mixed_120_board_sha256"])

    def test_exhibition_entry_course_changes_conditional_board_only_when_activated(self):
        # These are EXHIBITION courses by boat, not boat numbers or final entry.
        # #1692's official K study documented that boat 2 is not always course 2.
        plans = copy.deepcopy(self.plans)
        plans["third_attack"]["position_coefficients"]["entry_course"] = {
            "second": 0.35, "third": 0.15}
        original = self.run_lab(plans=plans)
        self.assertIn("entry_course",
                      original["feature_fields_actually_activated_by_scenario"]["third_attack"])
        self.assertTrue(original["exhibition_course_proxy_used_in_hypothesis"])
        self.assertFalse(original["two_course_wall_feature_or_final_entry_used"])
        self.assertIn("not_final_actual_entry", original["entry_course_input_semantics"])
        changed = copy.deepcopy(self.projection)
        changed["exhibition_features_by_boat"][0]["exhibition_course_only"] = 2
        changed["exhibition_features_by_boat"][1]["exhibition_course_only"] = 1
        with self.assertRaisesRegex(ValueError, "exhibition_projection_vector_digest_mismatch"):
            self.run_lab(projection=changed, plans=plans)
        changed["exhibition_features_sha256"] = hashlib.sha256(
            json.dumps(changed["exhibition_features_by_boat"], sort_keys=True,
                       separators=(",", ":"), ensure_ascii=False
                      ).encode("utf-8")
        ).hexdigest()
        after = self.run_lab(projection=changed, plans=plans)
        self.assertNotEqual(original["mode_result"]["mixed_120_board_sha256"],
                            after["mode_result"]["mixed_120_board_sha256"])
        self.assertFalse(after["actual_entry_wind_tide_motor_or_wall_used"])
        self.assertFalse(after["forecast_usable"])
        self.assertFalse(after["formal"])

        # The exact same course-switch must have NO effect at zero coefficient.
        zero_plans = copy.deepcopy(plans)
        zero_plans["third_attack"]["position_coefficients"]["entry_course"] = {
            "second": 0.0, "third": 0.0}
        base = self.run_lab(plans=zero_plans)
        switched = self.run_lab(projection=changed, plans=zero_plans)
        self.assertEqual(base["mode_result"]["mixed_120_board_sha256"],
                         switched["mode_result"]["mixed_120_board_sha256"])
        self.assertFalse(switched["exhibition_course_proxy_used_in_hypothesis"])
        self.assertIn("exhibition_course_only",
                      switched["projection_features_present_but_not_scored"])

    def test_duplicate_exhibition_courses_stay_rejected_with_rehashed_projection(self):
        changed = copy.deepcopy(self.projection)
        changed["exhibition_features_by_boat"][1]["exhibition_course_only"] = 1
        changed["exhibition_features_sha256"] = hashlib.sha256(
            json.dumps(changed["exhibition_features_by_boat"], sort_keys=True,
                       separators=(",", ":"), ensure_ascii=False
                      ).encode("utf-8")
        ).hexdigest()
        with self.assertRaisesRegex(ValueError, "exhibition_roster_not_six_distinct"):
            self.run_lab(projection=changed)

    def test_weight_hypotheses_change_mixture_without_forced_variation(self):
        first = self.run_lab()
        changed = copy.deepcopy(self.plans)
        changed["escape_wall"]["weight"] = .25
        changed["third_attack"]["weight"] = .55
        second = self.run_lab(plans=changed)
        self.assertNotEqual(first["mode_result"]["mixed_120_board_sha256"],
                            second["mode_result"]["mixed_120_board_sha256"])
        self.assertFalse(second["model_probabilities_calibrated"])

    def test_weather_tide_and_actual_entry_cannot_be_forged(self):
        for field in ("tide_height_cm", "wind_speed_mps",
                      "actual_entry_course", "two_course_wall_rate"):
            plans = copy.deepcopy(self.plans)
            plans["third_attack"]["position_coefficients"][field] = {
                "second": .8, "third": .2}
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.run_lab(plans=plans)
        bad = copy.deepcopy(self.projection)
        bad["missing_research_features"].remove("tide_phase")
        with self.assertRaises(ValueError):
            self.run_lab(projection=bad)
        bad = copy.deepcopy(self.projection)
        bad["raw_http_origin_independently_attested"] = True
        with self.assertRaises(ValueError):
            self.run_lab(projection=bad)

    def test_corrupted_projection_roster_is_rejected(self):
        cases = []
        bad = copy.deepcopy(self.projection)
        bad["exhibition_features_by_boat"][1]["boat"] = 1
        cases.append(bad)
        bad = copy.deepcopy(self.projection)
        bad["exhibition_features_by_boat"][0]["exhibition_st_s"] = None
        cases.append(bad)
        bad = copy.deepcopy(self.projection)
        bad["exhibition_features_by_boat"].append(
            copy.deepcopy(bad["exhibition_features_by_boat"][0]))
        cases.append(bad)
        for bad in cases:
            with self.assertRaises(ValueError):
                self.run_lab(projection=bad)

    def test_fake_conditional_formal_and_head_mass_are_rejected(self):
        def fake_formal(*args):
            d = self.condition(*args)
            d["formal"] = True
            return d
        with self.assertRaises(ValueError):
            self.run_lab(callback=fake_formal)

        def fake_head(*args):
            d = self.condition(*args)
            altered = hypothetical_head_board(
                d["ranked_board"], [1.5, 0, 0, 0, 0, 0],
                study_id="EXPLORATORY_ONLY_MALICIOUS_CALLBACK")
            d["ranked_board"] = altered["ranked_board"]
            return d
        with self.assertRaises(ValueError):
            self.run_lab(callback=fake_head)

    def test_national_rates_are_unproven_and_no_odds_used_for_ranking(self):
        out = self.run_lab()
        self.assertFalse(out["national_rates_predeadline_original_independently_verified"])
        self.assertFalse(out["conditional_callback_module_identity_independently_verified"])
        self.assertFalse(out["conditional_callback_result_blind_independently_verified"])
        self.assertFalse(out["actual_official_exhibition_consumption_independently_replayed"])
        self.assertFalse(out["mode_result"]["separate_scenario_hole_research"]["official_odds_used"])
        self.assertFalse(out["mode_result"]["separate_scenario_hole_research"]["expected_value_claim"])
        self.assertEqual(out["feature_fields_passed_to_conditional_lab"],
                         ["entry_course", "exhibition_st_s", "exhibition_time_s"])
        self.assertFalse(out["exhibition_course_proxy_used_in_hypothesis"])
        self.assertIn("exhibition_course_only", out["projection_features_present_but_not_scored"])
        self.assertFalse(out["two_course_wall_feature_or_final_entry_used"])
        self.assertNotIn("exhibition_time_s", out["projection_features_present_but_not_scored"])
        self.assertEqual(out["exhibition_time_s_status"],
                         "available_for_explicit_hypothesis_only")

    def test_scenario_weights_must_be_explicit_and_sum_to_one(self):
        plans = copy.deepcopy(self.plans)
        plans["escape_wall"]["weight"] = .9
        with self.assertRaises(ValueError):
            self.run_lab(plans=plans)
        plans = copy.deepcopy(self.plans)
        plans["escape_wall"]["head_log_shifts"] = [0, 0, 0, 0, 0]
        with self.assertRaises(ValueError):
            self.run_lab(plans=plans)


if __name__ == "__main__":
    unittest.main()
