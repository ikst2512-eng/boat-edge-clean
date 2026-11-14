"""Synthetic contract for real prior-day rate -> unfitted 120 matrix."""
import copy
import unittest

from scenario_prior_day_meeting_matrix_replay import replay_prior_day_form_into_unfitted_matrix
from scenario_official_meeting_form_research import extract_prior_day_meeting_form
from test_scenario_official_meeting_form_research import original_like_racelist, IDS, RACE


def context():
    history = extract_prior_day_meeting_form(original_like_racelist(), RACE, IDS)
    source = {
        "beforeinfo": {"sha256":"a"*64,"received_at_jst":"2026-11-14T20:21:03+09:00"},
        "odds": {"sha256":"b"*64,"received_at_jst":"2026-11-14T20:21:11+09:00"},
        "racelist":{"sha256": history["racelist_original_sha256"],
                    "received_at_jst":"2026-11-14T20:21:20+09:00"},
    }
    manifest = {
        "schema":"OFFICIAL_REAUDITED_INPUT_MANIFEST_V1","race_code":RACE,
        "cutoff_jst":"2026-11-14T20:26:00+09:00",
        "formal_t12_certified":False,"official_source_fields_reconstructed":True,
        "official_sources":source,
        "six_boat_inputs":[{"lane":i,"registration":reg,"exhibition_course":i}
                           for i,reg in enumerate(IDS,1)],
    }
    shadow = {
        "race_code":RACE,"generated":True,
        "generated_at_jst":"2026-11-14T20:21:39+09:00",
        "t12_cutoff_jst":"2026-11-14T20:26:00+09:00",
        "research_only":True,"formal_t12_certified":False,
        "model_accuracy_verified":False,
    }
    return history,manifest,shadow


class MeetingMatrixTests(unittest.TestCase):
    def test_counted_meeting_rates_enter_only_research_120(self):
        historical, manifest, shadow=context()
        result=replay_prior_day_form_into_unfitted_matrix(
            historical,manifest,shadow,manifest["cutoff_jst"])
        self.assertEqual(result["matrix"]["count"],120)
        self.assertFalse(result["matrix"]["predicted_probabilities"])
        self.assertFalse(result["new_forecast_generated"])
        self.assertFalse(result["model_coefficients_fitted"])
        self.assertFalse(result["formal"])
        rows={r["ticket"]:r["features"] for r in result["matrix"]["rows"]}
        self.assertEqual(rows["1-2-3"]["head_meeting_2ren"],.5)
        self.assertEqual(rows["1-2-3"]["second_meeting_2ren"],.5)
        self.assertEqual(rows["1-2-3"]["third_meeting_2ren"],.5)
        self.assertEqual(rows["1-2-3"]["head_meeting_st_s"],.15)
        self.assertIsNone(rows["1-2-3"]["head_motor_2ren"])
        self.assertIsNone(rows["1-2-3"]["escape_two_escape_assist_proxy"])
        self.assertIsNone(rows["3-4-5"]["third_makuri_head"])
        self.assertTrue(result["counted_meeting_form_actually_consumed_by_feature_matrix"])
        self.assertTrue(result["motor_rates_not_consumed_without_denominators"])

    def test_changed_prior_result_changes_features_without_calibration(self):
        raw=original_like_racelist()
        changed=raw.replace('>１</a>'.encode(),'>４</a>'.encode(),1)
        original, manifest, shadow=context()
        amended=extract_prior_day_meeting_form(changed,RACE,IDS)
        # A genuine different original must have different SHA in manifest.
        manifest["official_sources"]["racelist"]["sha256"]=amended["racelist_original_sha256"]
        first=replay_prior_day_form_into_unfitted_matrix(
            original,context()[1],shadow,manifest["cutoff_jst"])
        second=replay_prior_day_form_into_unfitted_matrix(
            amended,manifest,shadow,manifest["cutoff_jst"])
        self.assertNotEqual(first["feature_matrix_sha256"],second["feature_matrix_sha256"])
        self.assertEqual(original["rows"][0]["prior_day_top2_count"],1)
        self.assertEqual(amended["rows"][0]["prior_day_top2_count"],0)
        self.assertFalse(second["new_forecast_generated"])

    def test_wrong_race_roster_digest_and_cutoff_denied(self):
        for location in ("race","registration","sha","cutoff","after"):
            meeting, manifest, shadow=context()
            if location=="race": meeting["race_code"]="202611140711"
            if location=="registration": manifest["six_boat_inputs"][0]["registration"]="4999"
            if location=="sha": manifest["official_sources"]["racelist"]["sha256"]="f"*64
            if location=="cutoff": shadow["t12_cutoff_jst"]="2026-11-14T20:27:00+09:00"
            if location=="after": shadow["generated_at_jst"]="2026-11-14T20:26:00+09:00"
            with self.subTest(location=location),self.assertRaises(ValueError):
                replay_prior_day_form_into_unfitted_matrix(
                    meeting,manifest,shadow,manifest["cutoff_jst"])

    def test_future_or_forged_sample_cannot_enter_feature_matrix(self):
        for change in ("fake_n", "fake_top2", "future", "formal", "source_after_generation"):
            meeting,manifest,shadow=context()
            if change=="fake_n": meeting["rows"][0]["prior_day_completed_starts"]=50
            if change=="fake_top2": meeting["rows"][0]["prior_day_top2_count"]=2
            if change=="future": meeting["rows"][0]["prior_day_results"][0]["race_code"]=RACE
            if change=="formal": shadow["formal_t12_certified"]=True
            if change=="source_after_generation":
                manifest["official_sources"]["racelist"]["received_at_jst"]="2026-11-14T20:22:00+09:00"
            with self.subTest(change=change),self.assertRaises(ValueError):
                replay_prior_day_form_into_unfitted_matrix(
                    meeting,manifest,shadow,manifest["cutoff_jst"])


if __name__=="__main__":
    unittest.main()
