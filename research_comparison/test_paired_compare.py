import sys
import copy
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from paired_compare import TICKETS, compare

class PairedComparisonTests(unittest.TestCase):
    def row(self):
        p={t:1/120 for t in TICKETS}
        base={"model_id":"a","model_sha":"a"*40,"input_sha256":"b"*64,
              "first_git_commit":"c"*40,"first_git_saved_at":"2026-10-28T12:00:00+09:00",
              "generated_at":"2026-10-28T11:59:00+09:00",
              "source_received_at":"2026-10-28T11:58:00+09:00",
              "independently_verified":True,"probabilities":p}
        return {"race_key":"20261028-12-1","deadline":"2026-10-28T13:00:00+09:00",
                "input_sha256":"b"*64,"research_outcome_access_approved":True,
                "outcome_independently_verified":True,"candidate_pre_registered":True,
                "result":"1-2-3",
                "pre_registration":{"baseline_model_id":"a","candidate_model_id":"b",
                    "baseline_model_sha":"a"*40,"candidate_model_sha":"a"*40,
                    "registered_at":"2026-10-28T11:50:00+09:00",
                    "receipt_verified_independently":True},
                "forecasts":{"a":base,"b":dict(copy.deepcopy(base),model_id="b")}}
    def test_model_probability_inputs_are_independent(self):
        row=self.row()
        self.assertIsNot(row["forecasts"]["a"]["probabilities"],
                         row["forecasts"]["b"]["probabilities"])
    def test_identical_models_have_zero_paired_delta(self):
        o=compare([self.row()],"a","b")
        self.assertEqual(o["eligible_races"],1)
        self.assertEqual(o["metrics"]["top10"]["delta"],0)
        self.assertAlmostEqual(o["metrics"]["log_loss"]["delta"],0)
        self.assertAlmostEqual(o["metrics"]["multiclass_brier"]["delta"],0)
    def test_brier_penalizes_wrong_concentrated_forecast(self):
        r=self.row()
        y=r["result"]
        for name in ("a","b"):
            p=r["forecasts"][name]["probabilities"]
            p.update({t:0.1/119 for t in TICKETS})
            p[y]=0.9 if name=="a" else 0.1/119
            if name=="b":
                wrong=next(t for t in TICKETS if t != y)
                p[wrong]=0.9
        result=compare([r],"a","b")
        self.assertGreater(result["metrics"]["multiclass_brier"]["delta"],0)
        self.assertGreater(result["metrics"]["log_loss"]["delta"],0)
    def test_post_deadline_freeze_rejected(self):
        r=self.row()
        r["forecasts"]["b"]["first_git_saved_at"]="2026-10-28T13:01:00+09:00"
        o=compare([r],"a","b")
        self.assertEqual(o["eligible_races"],0)
        self.assertEqual(o["status"],"INSUFFICIENT_EVIDENCE")
    def test_incomplete_probability_distribution_rejected(self):
        r=self.row()
        r["forecasts"]["b"]["probabilities"]={"1-2-3":1.0}
        self.assertEqual(compare([r],"a","b")["eligible_races"],0)
    def test_sha_drift_rejected(self):
        first=self.row()
        second=self.row()
        second["race_key"]="20261028-12-2"
        second["forecasts"]["b"]["model_sha"]="d"*40
        o=compare([first,second],"a","b")
        self.assertEqual(o["eligible_races"],1)
        self.assertEqual(o["excluded_races"],1)
    def test_generated_after_first_freeze_rejected(self):
        r=self.row()
        r["forecasts"]["b"]["generated_at"]="2026-10-28T12:01:00+09:00"
        self.assertEqual(compare([r],"a","b")["eligible_races"],0)
    def test_unbound_registration_rejected(self):
        r=self.row()
        r["pre_registration"]["candidate_model_sha"]="d"*40
        self.assertEqual(compare([r],"a","b")["eligible_races"],0)
    def test_registration_after_forecast_rejected(self):
        r=self.row()
        r["pre_registration"]["registered_at"]="2026-10-28T12:01:00+09:00"
        self.assertEqual(compare([r],"a","b")["eligible_races"],0)
    def test_duplicate_race_excluded(self):
        first=self.row()
        duplicate=self.row()
        result=compare([first,duplicate],"a","b")
        self.assertEqual(result["eligible_races"],0)
        self.assertEqual(result["excluded_races"],2)
    def test_unverified_registration_receipt_rejected(self):
        r=self.row()
        r["pre_registration"]["receipt_verified_independently"]=False
        self.assertEqual(compare([r],"a","b")["eligible_races"],0)
    def test_mismatched_race_input_digest_rejected(self):
        r=self.row()
        r["forecasts"]["b"]["input_sha256"]="f"*64
        self.assertEqual(compare([r],"a","b")["eligible_races"],0)
    def test_source_received_after_prediction_rejected(self):
        r=self.row()
        r["forecasts"]["b"]["source_received_at"]="2026-10-28T12:01:00+09:00"
        self.assertEqual(compare([r],"a","b")["eligible_races"],0)
    def test_missing_source_receipt_timestamp_rejected(self):
        r=self.row()
        del r["forecasts"]["b"]["source_received_at"]
        self.assertEqual(compare([r],"a","b")["eligible_races"],0)
    def test_registration_drift_across_races_rejected(self):
        first=self.row()
        second=self.row()
        second["race_key"]="20261028-12-2"
        second["pre_registration"]["registered_at"]="2026-10-28T11:51:00+09:00"
        result=compare([first,second],"a","b")
        self.assertEqual(result["eligible_races"],1)
        self.assertEqual(result["excluded_races"],1)
        self.assertIn("pre-registration drift across evaluation races",result["exclusion_reasons"])
    def test_multiple_comparison_adjustment(self):
        result=compare([self.row()],"a","b")
        keys=("top1","top3","top5","top10","log_loss","multiclass_brier")
        self.assertEqual(len(keys),6)
        for name in keys:
            m=result["metrics"][name]
            self.assertGreaterEqual(m["holm_adjusted_p"],m["paired_signflip_p"])
            self.assertLessEqual(m["holm_adjusted_p"],1.0)
        self.assertIn("Holm",result["multiple_comparison_method"])
    def test_small_sample_never_labeled_comparative_evidence(self):
        output=compare([self.row()],"a","b")
        self.assertEqual(output["status"],"INSUFFICIENT_EVIDENCE")
        self.assertEqual(output["minimum_exploratory_sample"],30)
        self.assertIn("Small paired sample",output["sample_size_warning"])
    def test_same_model_cannot_be_compared_to_itself(self):
        with self.assertRaises(ValueError):
            compare([self.row()],"a","a")
    def test_registration_after_generation_before_freeze_rejected(self):
        r=self.row()
        r["pre_registration"]["registered_at"]="2026-10-28T11:59:30+09:00"
        result=compare([r],"a","b")
        self.assertEqual(result["eligible_races"],0)
        self.assertIn("pre-registration after forecast generation", result["exclusion_reasons"])
    def test_invalid_race_key_rejected(self):
        row=self.row()
        row["race_key"]="ambiguous-race"
        self.assertEqual(compare([row],"a","b")["eligible_races"],0)
    def test_impossible_calendar_date_rejected(self):
        row=self.row()
        row["race_key"]="20260230-12-1"
        self.assertEqual(compare([row],"a","b")["eligible_races"],0)
    def test_venue_and_race_number_out_of_range_rejected(self):
        for key in ("20261028-25-1","20261028-12-13","20261028-00-1"):
            row=self.row()
            row["race_key"]=key
            self.assertEqual(compare([row],"a","b")["eligible_races"],0)
    def test_deadline_jst_date_mismatch_rejected(self):
        row=self.row()
        row["deadline"]="2026-10-29T13:00:00+09:00"
        self.assertEqual(compare([row],"a","b")["eligible_races"],0)
    def test_invalid_row_cannot_suppress_later_valid_same_race(self):
        invalid=self.row()
        invalid["research_outcome_access_approved"]=False
        valid=self.row()
        result=compare([invalid,valid],"a","b")
        self.assertEqual(result["eligible_races"],0)
        self.assertEqual(result["excluded_races"],2)
        self.assertIn("ambiguous duplicate race",result["exclusion_reasons"])
    def test_exclusion_audit_details_without_outcomes(self):
        row=self.row()
        row["research_outcome_access_approved"]=False
        result=compare([row],"a","b")
        self.assertEqual(result["excluded_details"],[
            {"race_key":"20261028-12-1","reason":"outcome access not approved"}])
        self.assertNotIn("1-2-3",str(result["excluded_details"]))
    def test_unapproved_outcome_rejected(self):
        r=self.row()
        r["research_outcome_access_approved"]=False
        self.assertEqual(compare([r],"a","b")["eligible_races"],0)

if __name__ == "__main__":
    unittest.main()
