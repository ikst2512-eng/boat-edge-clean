"""No-network tests for a NEW exploratory F/L display-only feature.

No forecasts, odds-driven ranks, outcome reads, remote writes, or attempts to
relax the pinned #1693/#1710 source/model admission.
"""
import hashlib
import json
import unittest

from scenario_flagged_st_feature_study import encode_signed_st_only
from test_scenario_official_st_intake_diagnostic import fixture


class FlaggedSTSignedFeatureOnlyTests(unittest.TestCase):
    def test_real_shape_five_F_signed_and_original_labels_preserved(self):
        a, raw, meta = fixture(["F.05","F.11",".10","F.02","F.04","F.03"])
        x = encode_signed_st_only(a, raw, meta)
        self.assertEqual(x["flag_F_count"], 5)
        self.assertEqual(x["flag_L_count"], 0)
        self.assertEqual(x["numeric_display_count"], 1)
        self.assertEqual(
            [r["signed_st_seconds_decimal_string"] for r in x["exhibition_st_by_boat"]],
            ["-0.05","-0.11","0.10","-0.02","-0.04","-0.03"],
        )
        self.assertEqual(
            [r["official_st_raw"] for r in x["exhibition_st_by_boat"]],
            ["F.05","F.11",".10","F.02","F.04","F.03"],
        )
        self.assertTrue(x["signed_numeric_available_for_all_six"])
        self.assertFalse(x["flagged_display_is_main_race_F_or_L"])
        self.assertFalse(x["production_changed"])
        self.assertFalse(x["formal"])

    def test_one_F_real_shape_does_not_turn_into_positive_st(self):
        a, raw, meta = fixture([".25",".15",".09",".06",".06","F.03"])
        x = encode_signed_st_only(a, raw, meta)
        self.assertEqual(x["flag_F_count"], 1)
        self.assertEqual(x["exhibition_st_by_boat"][-1]["signed_st_seconds_decimal_string"],"-0.03")
        self.assertEqual(x["exhibition_st_by_boat"][-1]["display_class"],"F")
        self.assertFalse(x["exhibition_st_by_boat"][-1]["numeric_model_input_authorized"])

    def test_L_preserves_uninterpreted_without_imputed_one_second(self):
        a, raw, meta = fixture(["L.03",".02",".03",".04",".05",".06"])
        x = encode_signed_st_only(a, raw, meta)
        self.assertEqual(x["flag_L_count"], 1)
        self.assertIsNone(x["exhibition_st_by_boat"][0]["signed_st_seconds_decimal_string"])
        self.assertEqual(x["exhibition_st_by_boat"][0]["official_st_raw"],"L.03")
        self.assertFalse(x["signed_numeric_available_for_all_six"])
        self.assertFalse(x["L_display_time_offset_independently_verified"])

    def test_negative_zero_retains_F_display_flag(self):
        a, raw, meta = fixture(["F.00",".01",".02",".03",".04",".05"])
        x = encode_signed_st_only(a, raw, meta)
        self.assertEqual(x["exhibition_st_by_boat"][0]["signed_st_seconds_decimal_string"],"-0.00")
        self.assertEqual(x["exhibition_st_by_boat"][0]["display_class"],"F")

    def test_all_six_normal_no_untested_predictions(self):
        a, raw, meta = fixture()
        x = encode_signed_st_only(a, raw, meta)
        self.assertEqual((x["flag_F_count"],x["flag_L_count"],x["numeric_display_count"]),(0,0,6))
        self.assertTrue(x["signed_numeric_available_for_all_six"])
        self.assertTrue(all(v["display_class"]=="normal" for v in x["exhibition_st_by_boat"]))
        for claim in ("model_executed", "candidate_created",
                      "eligible_for_existing_300_plus_300", "formal",
                      "accuracy_improvement_proven", "production_changed"):
            self.assertFalse(x[claim])

    def test_original_sha_and_vector_are_deterministic(self):
        a, raw, meta = fixture(["F.04",".02",".03",".04",".05",".06"])
        x = encode_signed_st_only(a, raw, meta)
        self.assertEqual(x,encode_signed_st_only(a, raw, meta))
        self.assertEqual(x["beforeinfo_source_sha256"],hashlib.sha256(raw).hexdigest())
        self.assertEqual(len(x["vector_sha256"]),64)
        a2, raw2, meta2 = fixture(["F.05",".02",".03",".04",".05",".06"])
        self.assertNotEqual(x["vector_sha256"],encode_signed_st_only(a2,raw2,meta2)["vector_sha256"])

    def test_incomplete_official_input_no_signed_feature(self):
        a, raw, meta = fixture()
        a["component_checks"]["odds_120"]=False
        a["all_research_components_observed_by_t12"]=False
        a["missing_components"]=["odds_120"]
        with self.assertRaisesRegex(ValueError, "requires_all_three_complete"):
            encode_signed_st_only(a,raw,meta)

    def test_wrong_sha_and_receipt_cannot_be_encoded(self):
        a, raw, meta = fixture()
        meta["sha256"]="0"*64
        with self.assertRaisesRegex(ValueError,"manifest_not_identical"):
            encode_signed_st_only(a,raw,meta)
        a,raw,meta=fixture()
        meta["received_at_jst"]="2026-11-11T19:55:00+09:00"
        with self.assertRaisesRegex(ValueError,"manifest_not_identical"):
            encode_signed_st_only(a,raw,meta)

    def test_flagged_ST_bad_identity_and_ambiguous_rejected(self):
        a,raw,meta=fixture(["F0.05",".02",".03",".04",".05",".06"])
        with self.assertRaisesRegex(ValueError,"unsupported_start_syntax"):
            encode_signed_st_only(a,raw,meta)
        a,raw,meta=fixture()
        a["exhibition_course_to_boat"]["1"]="6"
        with self.assertRaisesRegex(ValueError,"course_mismatch"):
            encode_signed_st_only(a,raw,meta)

    def test_report_has_no_ticket_or_result_keys(self):
        a,raw,meta=fixture(["F.05",".02",".03",".04",".05",".06"])
        x=encode_signed_st_only(a,raw,meta)
        wire=json.dumps(x,sort_keys=True)
        for key in ('"winning_ticket"','"finish_order"','"payout"',
                    '"predictions"','"ranked_modes"','"probabilities"'):
            self.assertNotIn(key,wire)


if __name__ == "__main__":
    unittest.main()
