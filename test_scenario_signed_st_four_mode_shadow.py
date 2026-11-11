"""Signed-F four-mode SHADOW tests. Synthetic source; pinned 1698 if present.

Synthetic fixtures never count as an official T-12 source, receipt, genuine
historical prediction, scored hit or prospective candidate.
"""
import copy
import hashlib
import importlib
import json
import os
import unittest

from scenario_flagged_st_feature_study import encode_signed_st_only
from scenario_signed_st_four_mode_shadow import (
    _signed_vector, signed_F_four_mode_math, STUDY_ID, BUDGETS,
)
from test_scenario_official_st_intake_diagnostic import fixture
from test_scenario_mode_specific_exhibition_end_to_end import hypotheses, weights

RATES=[5.2,5.9,6.4,4.7,5.5,5.1]
TIMES=[6.78,6.83,6.85,6.78,6.81,6.77]


def feature(st=None):
    a,raw,manifest=fixture(st or ["F.05","F.11",".10","F.02","F.04","F.03"])
    return encode_signed_st_only(a,raw,manifest)


class FlaggedSTFailClosedTests(unittest.TestCase):
    def test_real_shape_flags_have_correct_sign(self):
        signed=feature()
        self.assertEqual(_signed_vector(signed),[-.05,-.11,.10,-.02,-.04,-.03])

    def test_raw_display_tampering_fails_sha_gate(self):
        f=feature()
        f["exhibition_st_by_boat"][0]["official_st_raw"]="F.04"
        with self.assertRaisesRegex(ValueError,"vector_sha256_mismatch"):
            _signed_vector(f)

    def test_wrong_sign_cannot_hide_behind_rehashed_vector(self):
        f=feature()
        f["exhibition_st_by_boat"][0]["signed_st_seconds_decimal_string"]="0.05"
        f["vector_sha256"]=hashlib.sha256(json.dumps({
            "race_code":f["race_code"],
            "beforeinfo_source_sha256":f["beforeinfo_source_sha256"],
            "exhibition_st_by_boat":f["exhibition_st_by_boat"],
        },sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
        with self.assertRaisesRegex(ValueError,"not_bound_to_display"):
            _signed_vector(f)

    def test_L_is_not_numeric_or_imputed(self):
        f=feature(["L.03",".11",".10",".02",".04",".03"])
        with self.assertRaisesRegex(ValueError,"L_flag_no_unambiguous_numeric_seconds"):
            _signed_vector(f)

    def test_outside_pinned_1698_numeric_range_rejected_not_clipped(self):
        f=feature(["F.98",".11",".10",".02",".04",".03"])
        with self.assertRaisesRegex(ValueError,"outside_pinned_1698"):
            _signed_vector(f)

    def test_forecast_model_and_admission_flags_cannot_be_raised(self):
        f=feature()
        for field in ("model_executed","formal","candidate_created",
                      "eligible_for_existing_300_plus_300",
                      "official_first_remote_receipt_verified"):
            with self.subTest(field=field):
                t=copy.deepcopy(f)
                t[field]=True
                with self.assertRaisesRegex(ValueError,"formal_or_semantic"):
                    _signed_vector(t)

    def test_repeated_and_nonpermutation_exhibition_course_rejected(self):
        f=feature()
        f["exhibition_st_by_boat"][0]["exhibition_course_only"]=2
        f["vector_sha256"]=hashlib.sha256(json.dumps({
            "race_code":f["race_code"],
            "beforeinfo_source_sha256":f["beforeinfo_source_sha256"],
            "exhibition_st_by_boat":f["exhibition_st_by_boat"],
        },sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
        with self.assertRaisesRegex(ValueError,"flags_or_courses"):
            _signed_vector(f)

    def test_outcome_metadata_cannot_be_smuggled(self):
        f=feature()
        f["confirmed_result"]={"finish_order":[1,2,3]}
        with self.assertRaisesRegex(ValueError,"signed_feature_contract_invalid"):
            _signed_vector(f)


class Pinned1698SignedFMathTests(unittest.TestCase):
    def setUp(self):
        if os.getenv("RESEARCH_1698_PIN_REQUIRED")!="1":
            self.skipTest("requires exact reviewed #1698 module SHA; never use ad-hoc math")
        try:
            m=importlib.import_module("position_sensitive_conditioned_lab")
        except ImportError as exc:
            self.fail("Pinned #1698 module absent "+str(exc))
        self.callback=m.experimental_conditional_board
        self.signed=feature()
        self.hypotheses=hypotheses()
        self.weights=weights()

    def run_math(self,signed=None,rates=None,times=None,scenarios=None,weights_map=None):
        return signed_F_four_mode_math(
            copy.deepcopy(self.signed if signed is None else signed),
            copy.deepcopy(RATES if rates is None else rates),
            copy.deepcopy(TIMES if times is None else times),
            copy.deepcopy(self.hypotheses if scenarios is None else scenarios),
            copy.deepcopy(self.weights if weights_map is None else weights_map),
            self.callback,study_id=STUDY_ID)

    def test_full_120_four_mode_probabilities_using_pinned_callback(self):
        result=self.run_math()
        self.assertEqual(result["study_id"],STUDY_ID)
        self.assertEqual(result["all_mode_tickets"],BUDGETS)
        self.assertEqual(set(result["four_mode_hypothetical_tickets"]),set(BUDGETS))
        self.assertEqual(len(result["scenario_120_boards"]),4)
        for mode,n in BUDGETS.items():
            board=result["four_mode_hypothetical_tickets"][mode]
            self.assertEqual(len(board["tickets"]),n)
            self.assertEqual(len({row["combo"] for row in board["tickets"]}),n)
            self.assertTrue(all(0<=row["p"]<=100 for row in board["tickets"]))
            self.assertEqual(board["top1"],board["tickets"][0]["combo"])
            self.assertEqual(len(board["full_120_mixture_sha256"]),64)
        self.assertTrue(result["model_math_executed"])
        self.assertFalse(result["candidate_created"])
        self.assertFalse(result["formal"])
        self.assertFalse(result["eligible_for_prior_600"])
        self.assertFalse(result["eligible_for_future_600"])
        self.assertFalse(result["betting_recommendation"])
        self.assertFalse(result["outcomes_read"])

    def test_signed_F_vs_positive_numeric_changes_second_third_probability(self):
        base=self.run_math()
        positive=feature([".05",".11",".10",".02",".04",".03"])
        updated=self.run_math(signed=positive)
        self.assertNotEqual(
            base["four_mode_hypothetical_tickets"]["narrow"]["full_120_mixture_sha256"],
            updated["four_mode_hypothetical_tickets"]["narrow"]["full_120_mixture_sha256"])
        self.assertEqual(base["all_mode_tickets"],updated["all_mode_tickets"])
        self.assertFalse(updated["official_first_remote_receipt_verified"])

    def test_frozen_first_head_does_not_consume_exhibition_ST_or_time(self):
        """Actual pinned #1698: ST/time alter SECOND/THIRD only, not first.

        This proves the current model is not yet an evidence-selected
        escape/wall/sashi/attack FIRST-HEAD model. No formal forecast.
        """
        from research_model import probabilities
        from scenario_first_head_research import hypothetical_head_board
        from scenario_four_mode_bridge import _valid_board
        original=feature()
        changed=feature(["F.19",".27",".03",".18",".11","F.02"])
        def evidence(signed,times):
            seconds=_signed_vector(signed)
            return {"boats":[{
                "boat":i,
                "exhibition_st_s":seconds[i-1],
                "exhibition_time_s":times[i-1],
                "entry_course":signed["exhibition_st_by_boat"][i-1]["exhibition_course_only"],
            } for i in range(1,7)],"context":{}}
        a=evidence(original,TIMES)
        b=evidence(changed,[6.9,6.7,6.8,6.9,6.7,6.8])
        different_within_head=0
        for name,plan in self.hypotheses.items():
            first=hypothetical_head_board(
                probabilities(RATES),plan["head_log_shifts"],
                study_id=STUDY_ID+"_HEAD_"+name.upper())
            coeffs=plan["position_coefficients"]
            one=self.callback(first["ranked_board"],a,coeffs,
                              STUDY_ID+"_PAIR_"+name.upper())
            two=self.callback(first["ranked_board"],b,coeffs,
                              STUDY_ID+"_PAIR_"+name.upper())
            mass1=_valid_board(one["ranked_board"])
            mass2=_valid_board(two["ranked_board"])
            for h in range(1,7):
                p1=sum(v for t,v in mass1.items() if t[0]==h)
                p2=sum(v for t,v in mass2.items() if t[0]==h)
                self.assertAlmostEqual(p1,p2,places=12,
                   msg="Current first-head mass should not be mislabeled as ST-driven")
            if any(abs(mass1[t]-mass2[t])>1e-8 for t in mass1):
                different_within_head+=1
        self.assertEqual(different_within_head,len(self.hypotheses))
        self.assertFalse(self.run_math()["accuracy_improvement_proven"])

    def test_registered_mode_world_weights_are_static_not_observed_wall(self):
        """Prevent a static scenario label from masquerading as wall evidence."""
        from pathlib import Path
        from scenario_future_local_candidate_handoff import _git_blob_sha1
        source=Path(__file__).resolve().parent/"research/four_mode_triple_source_forward_protocol_20261110.json"
        self.assertEqual(_git_blob_sha1(source.read_bytes()),
                         "bf60d2879065d1f9ecbd6b442db17fcb8fbcb8b7")
        method=json.loads(source.read_text(encoding="utf-8"))
        self.assertEqual(self.hypotheses,method["scenario_hypotheses"])
        self.assertEqual(self.weights,method["mode_weights"])
        self.assertEqual(set(self.hypotheses),{
            "escape_wall","two_sashi","third_attack","outer_benefit"})
        boosted={name:[i+1 for i,x in enumerate(plan["head_log_shifts"])
                       if x!=0] for name,plan in self.hypotheses.items()}
        self.assertEqual(boosted,{
            "escape_wall":[1],"two_sashi":[2],
            "third_attack":[3],"outer_benefit":[5]})
        # Neither the course/wall/entry nor wind, motor, wave or tide
        # is an ACTIVATED input to this pinned numeric head hypothesis.
        for plan in self.hypotheses.values():
            self.assertEqual(set(plan["position_coefficients"]),
                             {"exhibition_st_s","exhibition_time_s"})
            self.assertNotIn("two_course_wall_rate",plan["position_coefficients"])
            self.assertNotIn("entry_course",plan["position_coefficients"])
        for weights in self.weights.values():
            self.assertAlmostEqual(sum(weights.values()),1.0)
        self.assertFalse(self.run_math()["model_probabilities_calibrated"])

    def test_same_rates_different_exhibition_changes_full_board_not_head_shift(self):
        """Existing research reacts in conditional places; do not call it full."""
        changed=feature(["F.19",".27",".03",".18",".11","F.02"])
        before=self.run_math()
        after=self.run_math(signed=changed,
                            times=[6.9,6.7,6.8,6.9,6.7,6.8])
        self.assertEqual(before["scenario_120_boards"].keys(),
                         after["scenario_120_boards"].keys())
        self.assertEqual(before["active_features_by_scenario"],
                         after["active_features_by_scenario"])
        self.assertTrue(all(
            x==["exhibition_st_s","exhibition_time_s"]
            for x in before["active_features_by_scenario"].values()))
        self.assertNotEqual(
            before["four_mode_hypothetical_tickets"]["narrow"]["full_120_mixture_sha256"],
            after["four_mode_hypothetical_tickets"]["narrow"]["full_120_mixture_sha256"])
        self.assertFalse(after["official_first_remote_receipt_verified"])

    def test_same_input_is_deterministic_no_mode_fabricated_uniqueness(self):
        first=self.run_math()
        self.assertEqual(first,self.run_math())
        # Permitted mode overlap is not a model failure, and mode identity is
        # not changed to artificially force different winners.
        self.assertTrue(all(x["top1"] for x in first["four_mode_hypothetical_tickets"].values()))

    def test_L_and_bad_rates_do_not_reach_pinned_1698_math(self):
        with self.assertRaisesRegex(ValueError,"L_flag"):
            self.run_math(signed=feature(["L.03",".11",".10",".02",".04",".03"]))
        with self.assertRaisesRegex(ValueError,"six_racelist_national_rates"):
            self.run_math(rates=[5.2]*5)
        with self.assertRaisesRegex(ValueError,"six_official_exhibition_times"):
            self.run_math(times=[6.7]*5)

    def test_missing_world_weights_rejected(self):
        w=copy.deepcopy(self.weights)
        del w["hole"]
        with self.assertRaisesRegex(ValueError,"four_declared_weights"):
            self.run_math(weights_map=w)

    def test_output_always_disclaims_official_receipt_and_calibration(self):
        out=self.run_math()
        for name in ("official_same_race_racelist_rate_source_independently_verified",
                     "official_first_remote_receipt_verified",
                     "candidate_first_remote_receipt_verified",
                     "model_probabilities_calibrated","accuracy_improvement_proven",
                     "production_changed","promotion_allowed"):
            self.assertIs(out[name],False,name)


if __name__=="__main__":
    unittest.main()
