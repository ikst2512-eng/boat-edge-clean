"""Explicitly synthetic fixture tests; no official source or model output is fabricated as evidence."""
import base64
import copy
import hashlib
import json
import unittest
from itertools import permutations

from four_mode_official_future_lineage_preflight import (
    SCHEMA, preflight, _canonical, SIZES, has_embedded_outcome,
)


def fixture():
    # Test-only source bytes are NOT official HTML and must NEVER be recorded
    # as a successful official-source collection or prospective candidate.
    code = "202611100101"
    deadline = "2026-11-10T14:40:00+09:00"
    originals = {}
    for idx,kind in enumerate(("racelist","beforeinfo","odds120")):
        data = ("TEST_ONLY_NOT_OFFICIAL_" + kind).encode("ascii")
        originals[kind] = {
            "raw_base64": base64.b64encode(data).decode("ascii"),
            "sha256": hashlib.sha256(data).hexdigest(),
            "source_url": "https://www.boatrace.jp/TEST_ONLY_NOT_REAL_" + kind,
            "received_at_jst": "2026-11-10T14:25:%02d+09:00" % idx,
        }
    normalized = {
        "race_code": code,
        "source_sha256": {kind:item["sha256"]
                          for kind,item in originals.items()},
        "racelist_registration_ids": ["1234","2345","3456","4567","5678","6789"],
        "beforeinfo_registration_ids": ["1234","2345","3456","4567","5678","6789"],
        "exhibition_courses": [1,2,3,4,5,6],
        "exhibition_times": [6.5,6.6,6.7,6.8,6.9,7.0],
        "exhibition_st": [0.11,0.12,0.13,0.14,0.15,0.16],
        "exhibition_tilts": [-0.5,0.0,0.5,0.0,0.0,0.0],
        "odds_3t": {"-".join(p): float(i+1) for i,p
                    in enumerate(permutations("123456",3))},
    }
    tickets = list(normalized["odds_3t"])
    candidate = {
        "race_code": code, "deadline_jst": deadline,
        "generated_at_jst": "2026-11-10T14:25:05+09:00",
        "consumed_source_sha256": {kind:v["sha256"]
                                    for kind,v in originals.items()},
        "consumed_normalized_claim_sha256":
            hashlib.sha256(_canonical(normalized)).hexdigest(),
        "candidate_method_sha256": "a"*64,
        "candidate_tickets": {kind:tickets[:count] for kind,count in SIZES.items()},
        "formal":False,
    }
    return {"schema":SCHEMA,"race_code":code,"deadline_jst":deadline,
            "originals":originals,"normalized_source_claim":normalized}, candidate


class FutureLineagePreflightTests(unittest.TestCase):
    def test_synthetic_complete_but_never_formal(self):
        source,candidate = fixture()
        x=preflight(source,candidate)
        self.assertTrue(x["raw_originals_three_sha256_recalculated"])
        self.assertTrue(x["declared_candidate_source_hashes_match"])
        self.assertFalse(x["official_source_authenticity_independently_replayed"])
        self.assertFalse(x["actual_model_consumption_independently_replayed"])
        self.assertFalse(x["candidate_method_preregistered_before_generation_verified"])
        self.assertFalse(x["independent_first_remote_candidate_receipt_verified"])
        self.assertFalse(x["formal"])
        self.assertFalse(x["prospective_candidate_admitted"])
        self.assertEqual(x["formal_count"],0)

    def test_source_raw_mutation_and_wrong_base64_rejected(self):
        for mutation in ("bytes","base64","missing"):
            with self.subTest(mutation=mutation):
                s,c=fixture()
                if mutation=="bytes":
                    s["originals"]["odds120"]["raw_base64"]=base64.b64encode(b"CHANGED").decode()
                elif mutation=="base64":
                    s["originals"]["racelist"]["raw_base64"]="invalid?"
                else:
                    del s["originals"]["beforeinfo"]
                with self.assertRaises(ValueError):
                    preflight(s,c)

    def test_source_replay_claim_not_bound_to_raw_bytes(self):
        s,c=fixture()
        s["normalized_source_claim"]["source_sha256"]["beforeinfo"]="f"*64
        with self.assertRaisesRegex(ValueError,"normalized_claim_not_bound"):
            preflight(s,c)

    def test_candidates_must_declare_exact_raw_and_normalized_bytes(self):
        for mutation in ("source","parsed"):
            with self.subTest(mutation=mutation):
                s,c=fixture()
                if mutation=="source":
                    c["consumed_source_sha256"]["odds120"]="f"*64
                else:
                    c["consumed_normalized_claim_sha256"]="f"*64
                with self.assertRaisesRegex(ValueError,"candidate_declared_source"):
                    preflight(s,c)

    def test_no_cross_race_or_other_day_source(self):
        for mutation in ("code","deadline","receipt_day"):
            with self.subTest(mutation=mutation):
                s,c=fixture()
                if mutation=="code":
                    c["race_code"]="202611100102"
                elif mutation=="deadline":
                    c["deadline_jst"]="2026-11-10T15:40:00+09:00"
                else:
                    s["originals"]["odds120"]["received_at_jst"]="2026-11-09T14:25:02+09:00"
                with self.assertRaises(ValueError):
                    preflight(s,c)

    def test_missing_or_mismatched_six_entrants(self):
        for mutation in ("five","different","duplicated"):
            with self.subTest(mutation=mutation):
                s,c=fixture()
                ids=s["normalized_source_claim"]["beforeinfo_registration_ids"]
                if mutation=="five":
                    ids.pop()
                elif mutation=="different":
                    ids[0]="9999"
                else:
                    ids[0]=ids[1]
                with self.assertRaisesRegex(ValueError,"racer_identity_six"):
                    preflight(s,c)

    def test_exhibition_missing_or_nonfinite_rejected(self):
        for mutation in ("five_st","five_tilts","duplicate_course","nan"):
            with self.subTest(mutation=mutation):
                s,c=fixture()
                n=s["normalized_source_claim"]
                if mutation=="five_st":
                    n["exhibition_st"].pop()
                elif mutation=="five_tilts":
                    n["exhibition_tilts"].pop()
                elif mutation=="duplicate_course":
                    n["exhibition_courses"][-1]=5
                else:
                    n["exhibition_times"][0]=float("nan")
                with self.assertRaisesRegex(ValueError,"six_exhibition_entries"):
                    preflight(s,c)

    def test_119_or_invalid_odds_and_budget_rejected(self):
        for mutation in ("119","invalid_value","bad_budget","duplicate_ticket"):
            with self.subTest(mutation=mutation):
                s,c=fixture()
                if mutation=="119":
                    s["normalized_source_claim"]["odds_3t"].pop("1-2-3")
                elif mutation=="invalid_value":
                    s["normalized_source_claim"]["odds_3t"]["1-2-3"]=-1
                elif mutation=="bad_budget":
                    c["candidate_tickets"]["hit"].pop()
                else:
                    c["candidate_tickets"]["hit"][1]=c["candidate_tickets"]["hit"][0]
                with self.assertRaises(ValueError):
                    preflight(s,c)

    def test_source_and_model_generation_cutoff_boundaries(self):
        for mutation in ("source_late","candidate_before_source",
                         "candidate_same_second","candidate_late"):
            with self.subTest(mutation=mutation):
                s,c=fixture()
                if mutation=="source_late":
                    s["originals"]["odds120"]["received_at_jst"]="2026-11-10T14:28:00+09:00"
                elif mutation=="candidate_before_source":
                    c["generated_at_jst"]="2026-11-10T14:25:01+09:00"
                elif mutation=="candidate_same_second":
                    c["generated_at_jst"]="2026-11-10T14:25:03+09:00"
                else:
                    c["generated_at_jst"]="2026-11-10T14:28:00+09:00"
                with self.assertRaises(ValueError):
                    preflight(s,c)

    def test_source_normalization_cannot_include_results(self):
        s,c=fixture()
        s["normalized_source_claim"]["winning_ticket"]="1-2-3"
        with self.assertRaisesRegex(ValueError,"outcome_leak_in_normalized_claim"):
            preflight(s,c)

    def test_no_outcome_leak_or_fake_certifications(self):
        for field,value,target in (
            ("winning_ticket","1-2-3","candidate"),
            ("confirmed_result",{"finish":[1,2,3]},"source"),
            ("formal",True,"candidate"),
            ("formal",True,"source"),
            ("independent_first_remote_receipt_verified",True,"candidate"),
            ("official_source_authenticity_verified",True,"candidate"),
            ("model_input_consumption_independently_replayed",True,"candidate"),
        ):
            with self.subTest(field=field,target=target):
                s,c=fixture()
                (c if target=="candidate" else s)[field]=value
                with self.assertRaises(ValueError):
                    preflight(s,c)

    def test_unpinned_method_and_nonofficial_source_url(self):
        s,c=fixture()
        c["candidate_method_sha256"]="HEAD"
        with self.assertRaisesRegex(ValueError,"missing_method_byte_identity"):
            preflight(s,c)
        s,c=fixture()
        s["originals"]["beforeinfo"]["source_url"]="https://example.org/not_official"
        with self.assertRaisesRegex(ValueError,"missing_original_raw"):
            preflight(s,c)

    def test_nested_postrace_payload_never_passes_official_lineage(self):
        for location in ("source_original", "candidate_meta", "normalized_meta"):
            with self.subTest(location=location):
                source, candidate = fixture()
                if location == "source_original":
                    source["originals"]["beforeinfo"]["metadata"] = {
                        "audit": [{"official_result": [1, 2, 3]}]}
                elif location == "candidate_meta":
                    candidate["metadata"] = [{"environment": {
                        "post_race_weather": {"wind_mps": 8.0}}}]
                else:
                    source["normalized_source_claim"]["aux"] = {
                        "prior": {"finish_order": [1, 2, 3]}}
                with self.assertRaisesRegex(
                        ValueError,
                        "outcome_leak_in_normalized_claim"
                        if location == "normalized_meta" else
                        "outcome_or_forged_formal_in_pre_result_input"):
                    preflight(source, candidate)

    def test_embedded_outcome_guard_allows_pre_result_data_and_handles_cycles(self):
        source, candidate = fixture()
        self.assertFalse(has_embedded_outcome(source))
        self.assertFalse(has_embedded_outcome(candidate))
        self.assertFalse(has_embedded_outcome({
            "result_based_features_used": False, "exhibition_st": [0.12, 0.13]}))
        nested = {"audit": [{"inputs": {"payout": 12345}}]}
        self.assertTrue(has_embedded_outcome(nested))
        cycle = {"metadata": []}
        cycle["metadata"].append(cycle)
        self.assertFalse(has_embedded_outcome(cycle))


if __name__=="__main__":
    unittest.main()
