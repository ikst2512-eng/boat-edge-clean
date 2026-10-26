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
        return {"race_key":"r1","deadline":"2026-10-28T13:00:00+09:00",
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
        second["race_key"]="r2"
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
        self.assertEqual(result["eligible_races"],1)
        self.assertEqual(result["excluded_races"],1)
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
    def test_unapproved_outcome_rejected(self):
        r=self.row()
        r["research_outcome_access_approved"]=False
        self.assertEqual(compare([r],"a","b")["eligible_races"],0)

if __name__ == "__main__":
    unittest.main()
