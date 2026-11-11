"""Separate uncalibrated historical C1-head world sensitivity, never formal.

No real official K source replay, no prospectively saved candidate, no
target outcome or payout. The synthetic aggregation must not be mistaken
for #1692's historical October holdout or a predictive wall estimate.
"""
import copy
import importlib
import os
import unittest

from scenario_escape_prior_first_head_sensitivity import (
    historical_C1_escape_proxy, sensitivity_only, STUDY, K92_ZIP_SHA256,
)
from test_scenario_signed_st_four_mode_shadow import feature, RATES, TIMES
from test_scenario_mode_specific_exhibition_end_to_end import hypotheses
from unittest.mock import patch
import scenario_escape_prior_first_head_sensitivity as lab


def history():
    return {
        "schema":"UNATTESTED_BEFORE_EVENT_OFFICIAL_K_C1_HISTORY_SUMMARY_V1",
        "race_code":"202611111911",
        "historic_training_end_date_jst":"2026-09-30",
        "official_K_replay_zip_sha256_claim":K92_ZIP_SHA256,
        "venue_code":"19",
        "national_training_race_count":9241,
        "national_training_C1_escape_count":4985,
        "venue_training_race_count":405,
        "venue_training_C1_escape_count":220,
        "C1_athlete_registration":"4001",
        "C1_athlete_training_race_count":45,
        "C1_athlete_venue_centered_residual_sum":10.0,
        "exhibition_entry_roster_by_boat":[
            {"boat":i,"registration":str(4000+i),"exhibition_course":i}
            for i in range(1,7)],
        "training_used_outcomes_after_target":False,
        "official_source_receipt_independently_authenticated":False,
        "exhibition_is_final_race_entry":False,
        "outcomes_from_target_race_read":False,
    }


class StrictC1HistoricalEvidenceTests(unittest.TestCase):
    def test_residual_and_venue_components_are_explicit_and_bounded(self):
        e=historical_C1_escape_proxy(history(),feature())
        national=4985/9241
        venue=(220+40*national)/(405+40)
        expected=venue+10/(45+40)
        self.assertAlmostEqual(e["venue_C1_escape_proxy"],venue,places=12)
        self.assertAlmostEqual(e["athlete_adjusted_C1_escape_proxy"],expected,places=12)
        self.assertFalse(e["official_original_K_bytes_replayed_in_this_function"])
        self.assertFalse(e["exhibition_course_assumed_final_entry"])
        self.assertFalse(e["predictive_effect_proven"])

    def test_zero_historical_residual_is_exact_venue_control(self):
        h=history();h["C1_athlete_venue_centered_residual_sum"]=0.0
        e=historical_C1_escape_proxy(h,feature())
        self.assertEqual(e["venue_C1_escape_proxy"],
                         e["athlete_adjusted_C1_escape_proxy"])

    def test_lookahead_and_late_training_never_usable(self):
        for altered in ("2026-11-11","2026-11-10","2026-10-31","2026-07-31"):
            h=history();h["historic_training_end_date_jst"]=altered
            with self.subTest(date=altered), self.assertRaisesRegex(
                ValueError,"lookahead_or_untrained_period"):
                historical_C1_escape_proxy(h,feature())

    def test_requires_same_venue_race_and_registered_first_course_racer(self):
        for field,bad in (
            ("venue_code","07"),
            ("race_code","202611110711"),
            ("C1_athlete_registration","4002")
        ):
            h=history();h[field]=bad
            with self.subTest(field=field), self.assertRaises(ValueError):
                historical_C1_escape_proxy(h,feature())

    def test_changed_exhibition_entry_cannot_reuse_boat1_3point5_head_shift(self):
        h=history()
        h["exhibition_entry_roster_by_boat"][0]["exhibition_course"]=2
        h["exhibition_entry_roster_by_boat"][1]["exhibition_course"]=1
        with self.assertRaisesRegex(ValueError,"roster_or_exhibition_course_mismatch"):
            historical_C1_escape_proxy(h,feature())

    def test_missing_or_nonfinite_or_invalid_denominators_fail(self):
        for field,bad in (
            ("national_training_race_count",0),
            ("venue_training_race_count",0),
            ("venue_training_C1_escape_count",500),
            ("C1_athlete_training_race_count",-1),
            ("C1_athlete_venue_centered_residual_sum",float("nan")),
            ("C1_athlete_venue_centered_residual_sum",46),
        ):
            h=history();h[field]=bad
            with self.subTest(field=field),self.assertRaises(ValueError):
                historical_C1_escape_proxy(h,feature())

    def test_target_result_postrace_wind_and_provenance_forgery_denied(self):
        for field,bad in (
            ("outcomes_from_target_race_read",True),
            ("training_used_outcomes_after_target",True),
            ("official_source_receipt_independently_authenticated",True),
            ("exhibition_is_final_race_entry",True),
            ("target_finish_order",[1,2,3]),
            ("wind_after_race",3.0),
        ):
            h=history();h[field]=bad
            with self.subTest(field=field),self.assertRaisesRegex(
                ValueError,"source_claim_or_schema_forbidden"):
                historical_C1_escape_proxy(h,feature())

    def test_frozen_existing_world_protocol_is_enforced_before_math(self):
        h=history()
        with patch.object(lab,"FROZEN_1710_PROTOCOL_BLOB","0"*40):
            with self.assertRaisesRegex(ValueError,"frozen_1710_protocol_changed"):
                lab.sensitivity_only(h,feature(),RATES,TIMES,hypotheses(),None)
        plan=hypotheses()
        plan["escape_wall"]["position_coefficients"]["exhibition_st_s"]["second"]=.77
        with self.assertRaisesRegex(ValueError,"frozen_scenario_coefficients_not_identical"):
            lab.sensitivity_only(h,feature(),RATES,TIMES,plan,None)

    def test_roster_registration_duplicate_and_length_fail(self):
        h=history()
        h["exhibition_entry_roster_by_boat"][5]["registration"]="4001"
        with self.assertRaisesRegex(ValueError,"roster_or_exhibition_course_mismatch"):
            historical_C1_escape_proxy(h,feature())


class Pinned1698HistoricalC1HeadMathTests(unittest.TestCase):
    def setUp(self):
        if os.getenv("RESEARCH_1698_PIN_REQUIRED")!="1":
            self.skipTest("requires reviewed 1698 blob, no ad-hoc callback")
        self.callback=importlib.import_module(
            "position_sensitive_conditioned_lab").experimental_conditional_board

    def run_math(self,h=None):
        return sensitivity_only(h or history(),feature(),RATES,TIMES,
                                hypotheses(),self.callback)

    def test_athlete_history_changes_first_head_mass_and_full_120_probability(self):
        result=self.run_math()
        self.assertEqual(result["study_id"],STUDY)
        self.assertLess(result["control_head_mass_by_boat"]["1"],
                        result["hypothesis_head_mass_by_boat"]["1"])
        self.assertAlmostEqual(
            sum(result["control_head_mass_by_boat"].values()),1,places=12)
        self.assertAlmostEqual(
            sum(result["hypothesis_head_mass_by_boat"].values()),1,places=12)
        self.assertNotEqual(
            result["control_four_mode_tickets"]["narrow"]["full_120_mixture_sha256"],
            result["hypothesis_four_mode_tickets"]["narrow"]["full_120_mixture_sha256"])
        for name,count in result["same_mode_budgets"].items():
            self.assertEqual(len(result["control_four_mode_tickets"][name]["tickets"]),count)
            self.assertEqual(len(result["hypothesis_four_mode_tickets"][name]["tickets"]),count)
        for key in ("wall_effect_measured","actual_final_entry_verified",
                    "candidate_created","first_remote_receipt_verified",
                    "eligible_for_existing_600","eligible_for_new_600",
                    "outcomes_read","formal","production_changed",
                    "accuracy_improvement_proven"):
            self.assertIs(result[key],False,key)

    def test_zero_athlete_residual_keeps_all_120_boards_identical_to_control(self):
        h=history();h["C1_athlete_venue_centered_residual_sum"]=0.0
        result=self.run_math(h)
        self.assertEqual(result["control_head_mass_by_boat"],
                         result["hypothesis_head_mass_by_boat"])
        for mode in result["same_mode_budgets"]:
            self.assertEqual(
                result["control_four_mode_tickets"][mode]["full_120_mixture_sha256"],
                result["hypothesis_four_mode_tickets"][mode]["full_120_mixture_sha256"])

    def test_different_synthetic_athlete_history_is_deterministic(self):
        first=self.run_math()
        self.assertEqual(first,self.run_math())
        h=history();h["C1_athlete_venue_centered_residual_sum"]=-12
        second=self.run_math(h)
        self.assertLess(second["hypothesis_head_mass_by_boat"]["1"],
                        second["control_head_mass_by_boat"]["1"])

if __name__=="__main__":
    unittest.main()
