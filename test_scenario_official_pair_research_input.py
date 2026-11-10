"""Reject malformed partial official source claims; never certify two originals."""
import copy
import hashlib
import json
import unittest

from scenario_exhibition_all_mode_runner import _projected
from scenario_official_pair_research_input import PARTIAL_SCHEMA, SOURCE

def fixture():
    boats=[{
        "boat":i,
        "registration_id":str(3000+i),
        "exhibition_course_only":i,
        "exhibition_time_s":6.8+i/100,
        "exhibition_st_s":i/100,
        "exhibition_tilt":-0.5,
    } for i in range(1,7)]
    digest=lambda obj:hashlib.sha256(json.dumps(
        obj,sort_keys=True,separators=(",",":"),ensure_ascii=False
    ).encode()).hexdigest()
    return {
        "schema":PARTIAL_SCHEMA,
        "race_code":"202611101202",
        "source_sha256":{"beforeinfo":"a"*64,"odds120":"b"*64},
        "normalized_source_sha256":"c"*64,
        "exhibition_features_by_boat":boats,
        "exhibition_features_sha256":digest(boats),
        "structural_source_to_candidate_order":False,
        "structural_raw_semantic_replay_reported":False,
        "missing_research_features":[
            "actual_entry_course","motor_2ren_pct","wind_speed_mps",
            "wind_from_true_deg","start_heading_true_deg","wave_height_cm",
            "tide_station","tide_height_cm","tide_phase",
            "two_course_escape_assist_rate","two_course_wall_rate",
        ],
        "feature_values_imputed":False,
        "exhibition_is_actual_final_entry":False,
        "raw_http_origin_independently_attested":False,
        "replay_callback_authenticity_independently_proven":False,
        "candidate_first_remote_receipt_verified":False,
        "model_consumed_these_features_verified":False,
        "all_scenario_effect_coefficients_calibrated":False,
        "formal":False,"accuracy_effect_proven":False,
        "promotion_allowed":False,"production_changed":False,
        "source_original_zip_sha256":SOURCE["20261110"]["zip_sha"],
        "racelist_original_missing":True,
        "source_pair_only_no_new_forecast_receipt":True,
        "weather_observation_clock_unverified":True,
    }

class PartialOfficialProjectionContract(unittest.TestCase):
    def test_valid_exhibition_math_input_but_not_formal(self):
        d=fixture()
        self.assertEqual(len(_projected(d)),6)
        self.assertFalse(d["promotion_allowed"])
        self.assertFalse(d["structural_source_to_candidate_order"])

    def test_fabricated_racelist_hash_rejected(self):
        d=fixture();d["source_sha256"]["racelist"]="f"*64
        with self.assertRaisesRegex(ValueError,"projection_missing_original_fingerprints"):
            _projected(d)

    def test_missing_explicit_racelist_gap_rejected(self):
        d=fixture();d["racelist_original_missing"]=False
        with self.assertRaisesRegex(ValueError,"partial_official_source_must_fail_closed"):
            _projected(d)

    def test_forged_forecast_receipt_rejected(self):
        d=fixture();d["source_pair_only_no_new_forecast_receipt"]=False
        with self.assertRaisesRegex(ValueError,"partial_official_source_must_fail_closed"):
            _projected(d)

    def test_forged_weather_measurement_rejected(self):
        d=fixture();d["weather_observation_clock_unverified"]=False
        with self.assertRaisesRegex(ValueError,"partial_official_source_must_fail_closed"):
            _projected(d)

    def test_forged_full_replay_rejected(self):
        d=fixture();d["structural_raw_semantic_replay_reported"]=True
        with self.assertRaisesRegex(ValueError,"unsafe_or_unmatched_official_projection"):
            _projected(d)

    def test_source_to_forecast_clock_not_fabricated(self):
        d=fixture();d["structural_source_to_candidate_order"]=True
        with self.assertRaisesRegex(ValueError,"unsafe_or_unmatched_official_projection"):
            _projected(d)

    def test_promotion_is_forbidden(self):
        d=fixture();d["promotion_allowed"]=True
        with self.assertRaisesRegex(ValueError,"unsafe_or_unmatched_official_projection"):
            _projected(d)

    def test_exhibition_vector_digest_mutation_rejected(self):
        d=fixture();d["exhibition_features_by_boat"][1]["exhibition_st_s"]=.24
        with self.assertRaisesRegex(ValueError,"exhibition_projection_vector_digest_mismatch"):
            _projected(d)

    def test_unknown_result_field_rejected(self):
        d=fixture();d["winning_ticket"]="1-2-3"
        with self.assertRaisesRegex(ValueError,"unsafe_or_unmatched_official_projection"):
            _projected(d)

    def test_no_exhibition_values_may_be_imputed(self):
        d=fixture();d["feature_values_imputed"]=True
        with self.assertRaisesRegex(ValueError,"unsafe_or_unmatched_official_projection"):
            _projected(d)

if __name__=="__main__":
    unittest.main()
