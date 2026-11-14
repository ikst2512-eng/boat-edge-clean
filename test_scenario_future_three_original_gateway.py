"""Synthetic #1713 triple audit -> #1693 replay -> #1710/#1698 research.

No real official source, model accuracy, independent Git acceptance, or
registered future cohort is claimed by any fixture in this test module.
"""
import base64
import copy
from datetime import datetime, timedelta
import hashlib
import importlib
import json
import os
import unittest

from scenario_official_exhibition_projection import project_exhibition_research
from scenario_future_local_candidate_handoff import prepare_local_candidate
from test_scenario_future_protocol_freeze import read_protocol
from scenario_future_three_original_gateway import (
    CHECKS, STUDY, MIN_DAY, validate_audited_source_pairing,
    run_future_triple_experiment,
)
from test_scenario_official_exhibition_projection import fixture, replay_stub
from test_scenario_official_racelist_rates import synthetic_racelist, RATES
from test_scenario_mode_specific_exhibition_end_to_end import hypotheses, weights


def future_synthetic():
    source, candidate = fixture()
    def shift(v):
        if isinstance(v, str):
            return v.replace("2026-11-09","2026-11-11").replace(
                "20261109","20261111")
        if type(v) is dict:
            return {key:shift(x) for key,x in v.items()}
        if type(v) is list:
            return [shift(x) for x in v]
        return v
    source = shift(source)
    candidate = shift(candidate)
    normalized = source["normalized_source_claim"]
    # A fixture with real-like TD structure, NOT an official HTTP observation.
    # Ensure the model must use six source-HTML values rather than arbitrary
    # old V2 saved rates. Preserve the raw SHA/normalization chain.
    raw = synthetic_racelist(ids=normalized["racelist_registration_ids"],rates=RATES)
    digest=hashlib.sha256(raw).hexdigest()
    source["originals"]["racelist"]["raw_base64"]=base64.b64encode(raw).decode("ascii")
    source["originals"]["racelist"]["sha256"]=digest
    normalized["source_sha256"]["racelist"]=digest
    candidate["consumed_source_sha256"]["racelist"]=digest
    candidate["consumed_normalized_claim_sha256"] = hashlib.sha256(json.dumps(
        normalized, sort_keys=True, ensure_ascii=False,
        separators=(",",":")).encode()).hexdigest()
    assert candidate["race_code"].startswith(MIN_DAY)
    return source, candidate


def triple_fixture(source):
    code=source["race_code"]
    deadline=datetime.fromisoformat(source["deadline_jst"])
    cutoff=deadline-timedelta(minutes=12)
    stamps={x:source["originals"][x]["received_at_jst"]
            for x in ("racelist","beforeinfo","odds120")}
    latest=max(datetime.fromisoformat(x) for x in stamps.values())
    course=source["normalized_source_claim"]["exhibition_courses"]
    return {
        "race_code":code,
        "official_deadline_jst":deadline.isoformat(),
        "cutoff_jst":cutoff.isoformat(),
        "racelist_received_jst":stamps["racelist"],
        "beforeinfo_received_jst":stamps["beforeinfo"],
        "odds_received_jst":stamps["odds120"],
        "latest_original_received_jst":latest.isoformat(),
        "t12_receipt_margin_seconds":(cutoff-latest).total_seconds(),
        "registrations_by_lane":{
            str(i+1):str(x) for i,x in enumerate(
                source["normalized_source_claim"]["racelist_registration_ids"])},
        "exhibition_course_to_boat":{
            str(x):str(i+1) for i,x in enumerate(course)},
        "three_originals_hash_verified":True,
        "component_checks":{name:True for name in CHECKS},
        "missing_components":[],
        "all_research_components_observed_by_t12":True,
        "final_race_entry_verified":False,
        "full_t12_source_certified":False,
        "t12_eligible":False,
        "forecast_usable":False,
    }


class FutureTripleSourceGatewayTests(unittest.TestCase):
    def setUp(self):
        self.s,self.c = future_synthetic()
        self.audit=triple_fixture(self.s)
        self.projection=project_exhibition_research(self.s,self.c,replay_stub)

    def check(self, a=None, s=None, c=None, p=None):
        return validate_audited_source_pairing(
            self.audit if a is None else a,
            self.s if s is None else s,
            self.c if c is None else c,
            self.projection if p is None else p)

    def test_full_synthetic_cross_report_structural_handoff(self):
        before=copy.deepcopy((self.s,self.c,self.audit,self.projection))
        result=self.check()
        self.assertEqual(result["auditor_component_count"],12)
        self.assertTrue(result["registrations_matched_six"])
        self.assertTrue(result["exhibition_entry_permutation_matched"])
        self.assertEqual(result["race_code"],"202611111710")
        self.assertFalse(result["formal"])
        self.assertFalse(result["raw_HTTP_origin_independently_authenticated"])
        self.assertFalse(result["initial_remote_candidate_receipt_verified"])
        self.assertEqual(before,(self.s,self.c,self.audit,self.projection))

    def test_missing_each_official_component_rejected(self):
        for key in CHECKS:
            a=copy.deepcopy(self.audit)
            a["component_checks"][key]=False
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,"incomplete"):
                self.check(a=a)

    def test_wrong_race_historical_or_cross_join_rejected(self):
        a=copy.deepcopy(self.audit)
        a["race_code"]="202611091710"
        with self.assertRaisesRegex(ValueError,"not_future"):
            self.check(a=a)
        a=copy.deepcopy(self.audit)
        a["race_code"]="202611111711"
        with self.assertRaisesRegex(ValueError,"not_future"):
            self.check(a=a)

    def test_source_or_auditor_cannot_claim_formal(self):
        for key in ("final_race_entry_verified","full_t12_source_certified",
                    "t12_eligible","forecast_usable"):
            a=copy.deepcopy(self.audit)
            a[key]=True
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,"incomplete"):
                self.check(a=a)
        a=copy.deepcopy(self.audit)
        a["formal"]=True
        with self.assertRaisesRegex(ValueError,"contract"):
            self.check(a=a)
        a=copy.deepcopy(self.audit)
        a["winning_ticket"]="1-2-3"
        with self.assertRaisesRegex(ValueError,"contract"):
            self.check(a=a)

    def test_six_registration_identity_must_match_projection(self):
        a=copy.deepcopy(self.audit)
        a["registrations_by_lane"]["3"]="9900"
        with self.assertRaisesRegex(ValueError,"identity_or_entry_mismatch"):
            self.check(a=a)

    def test_exhibition_entry_is_not_final_entry(self):
        a=copy.deepcopy(self.audit)
        a["exhibition_course_to_boat"]["1"],a["exhibition_course_to_boat"]["2"]=(
            a["exhibition_course_to_boat"]["2"],
            a["exhibition_course_to_boat"]["1"])
        with self.assertRaisesRegex(ValueError,"identity_or_entry_mismatch"):
            self.check(a=a)

    def test_forged_extra_lane_and_missing_registration(self):
        a=copy.deepcopy(self.audit)
        a["registrations_by_lane"]["7"]="9999"
        with self.assertRaisesRegex(ValueError,"incomplete"):
            self.check(a=a)
        a=copy.deepcopy(self.audit)
        a["exhibition_course_to_boat"].pop("6")
        with self.assertRaisesRegex(ValueError,"incomplete"):
            self.check(a=a)

    def test_clocks_are_exact_independent_cross_checked(self):
        a=copy.deepcopy(self.audit)
        a["beforeinfo_received_jst"]="2026-11-11T15:02:01+09:00"
        with self.assertRaisesRegex(ValueError,"receipt_not_aligned"):
            self.check(a=a)
        a=copy.deepcopy(self.audit)
        a["latest_original_received_jst"]=a["beforeinfo_received_jst"]
        with self.assertRaisesRegex(ValueError,"latest_clock"):
            self.check(a=a)
        a=copy.deepcopy(self.audit)
        a["t12_receipt_margin_seconds"]=-3
        with self.assertRaisesRegex(ValueError,"latest_clock"):
            self.check(a=a)
        a=copy.deepcopy(self.audit)
        a["cutoff_jst"]="2026-11-11T15:15:00+09:00"
        with self.assertRaisesRegex(ValueError,"deadline"):
            self.check(a=a)
        a=copy.deepcopy(self.audit)
        a["racelist_received_jst"]="2026-11-11T15:01:00+00:00"
        with self.assertRaisesRegex(ValueError,"JST"):
            self.check(a=a)

    def test_source_missing_or_bad_digest_rejected(self):
        p=copy.deepcopy(self.projection)
        p["source_sha256"]["racelist"]="a"*64
        with self.assertRaisesRegex(ValueError,"digest"):
            self.check(p=p)
        s=copy.deepcopy(self.s)
        s["originals"].pop("racelist")
        with self.assertRaisesRegex(ValueError,"three_originals"):
            self.check(s=s)

    def test_rates_must_match_same_race_original_html(self):
        # Fake 5.0 fallback and borrowed rates from a different race are not
        # acceptable even with identical source/forecast clocks.
        with self.assertRaisesRegex(
                ValueError,"national_win_rates_or_registration"):
            run_future_triple_experiment(
                self.audit,self.s,self.c,replay_stub,[5.0]*6,
                hypotheses(),weights(),lambda *args:None)
        with self.assertRaisesRegex(
                ValueError,"national_win_rates_or_registration"):
            run_future_triple_experiment(
                self.audit,self.s,self.c,replay_stub,list(reversed(RATES)),
                hypotheses(),weights(),lambda *args:None)

    def test_result_leak_and_bad_rates_before_runner(self):
        for rates in ([5]*5,[5]*7,[5,5,5,-1,5,5],
                      [5,5,5,float("nan"),5,5], [5,5,5,"6",5,5]):
            with self.subTest(rates=rates), self.assertRaisesRegex(ValueError,"six_predeadline"):
                run_future_triple_experiment(
                    self.audit,self.s,self.c,replay_stub,rates,
                    hypotheses(),weights(),lambda *args: None)


class Pinned1698FutureGatewayIntegrationTests(unittest.TestCase):
    def test_synthetic_end_to_end_all_four_and_no_production(self):
        if os.environ.get("RESEARCH_1698_PIN_REQUIRED")!="1":
            self.skipTest("needs exact pinned #1698 source")
        source,candidate=future_synthetic()
        cb=importlib.import_module(
            "position_sensitive_conditioned_lab").experimental_conditional_board
        output=run_future_triple_experiment(
            triple_fixture(source),source,candidate,replay_stub,
            list(RATES),hypotheses(),weights(),cb)
        self.assertEqual(output["study_id"],STUDY)
        self.assertEqual(set(output["research_mode_tickets"]),
                         {"narrow","hit","balance","hole"})
        self.assertEqual({k:len(v["tickets"]) for k,v in
                          output["research_mode_tickets"].items()},
                         {"narrow":5,"hit":10,"balance":16,"hole":22})
        self.assertTrue(output["candidate_source_consumption_structurally_replayed"])
        self.assertTrue(output["national_win_rate_from_official_original_structurally_verified"])
        self.assertEqual(output["six_national_win_rates_from_same_original_html"],RATES)
        self.assertEqual(output["six_average_ST_from_same_original_html_not_scored"],[.16]*6)
        self.assertFalse(output["official_racelist_HTTP_authenticity_independently_verified"])
        self.assertRegex(output["model_input_content_sha256_research_only"],
                         r"^[0-9a-f]{64}$")
        self.assertRegex(output["four_mode_ranked_output_content_sha256_research_only"],
                         r"^[0-9a-f]{64}$")
        self.assertFalse(output["source_to_candidate_remote_receipt_proven"])
        local_handoff = prepare_local_candidate(
            output, read_protocol(), candidate["generated_at_jst"],
            "2026-11-11T15:08:00+09:00")
        self.assertEqual(local_handoff["race_code"],"202611111710")
        self.assertTrue(local_handoff["no_remote_write_performed"])
        self.assertFalse(local_handoff["candidate_first_remote_receipt_verified"])
        self.assertFalse(local_handoff["formal"])
        replay_handoff=prepare_local_candidate(
            output,read_protocol(),candidate["generated_at_jst"],
            "2026-11-11T15:08:00+09:00")
        self.assertEqual(local_handoff["bytes"],replay_handoff["bytes"])
        import json
        payload=json.loads(local_handoff["bytes"])
        self.assertEqual(
            payload["model_input_content_sha256"],
            output["model_input_content_sha256_research_only"])
        self.assertEqual(
            payload["four_mode_ranked_output_content_sha256"],
            output["four_mode_ranked_output_content_sha256_research_only"])
        repeated=run_future_triple_experiment(
            triple_fixture(source),source,candidate,replay_stub,
            list(RATES),hypotheses(),weights(),cb)
        self.assertEqual(
            output["model_input_content_sha256_research_only"],
            repeated["model_input_content_sha256_research_only"])
        self.assertEqual(
            output["four_mode_ranked_output_content_sha256_research_only"],
            repeated["four_mode_ranked_output_content_sha256_research_only"])
        modified_weights=weights()
        modified_weights["narrow"]["escape_wall"]=0.8
        modified_weights["narrow"]["two_sashi"]=0.2
        altered=run_future_triple_experiment(
            triple_fixture(source),source,candidate,replay_stub,
            list(RATES),hypotheses(),modified_weights,cb)
        self.assertNotEqual(
            output["model_input_content_sha256_research_only"],
            altered["model_input_content_sha256_research_only"])
        self.assertNotEqual(
            output["four_mode_ranked_output_content_sha256_research_only"],
            altered["four_mode_ranked_output_content_sha256_research_only"])
        for field in ("formal","forecast_usable",
                      "eligible_for_existing_1693_600_races",
                      "eligible_for_new_300_plus_300_races",
                      "candidate_remote_first_receipt_verified",
                      "hypotheses_frozen_in_prospective_registration",
                      "official_data_real_or_independently_authenticated",
                      "accuracy_improvement_proven",
                      "results_read","production_changed","promotion_allowed"):
            self.assertFalse(output[field],field)


if __name__=="__main__":
    unittest.main()
