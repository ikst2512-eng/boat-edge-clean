import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from paired_compare import TICKETS, compare

class PairedComparisonTests(unittest.TestCase):
    def row(self):
        p={t:1/120 for t in TICKETS}
        base={"model_id":"a","model_sha":"sha1","input_sha256":"same",
              "first_git_commit":"c1","first_git_saved_at":"2026-10-28T12:00:00+09:00",
              "generated_at":"2026-10-28T11:59:00+09:00",
              "independently_verified":True,"probabilities":p}
        return {"race_key":"r1","deadline":"2026-10-28T13:00:00+09:00",
                "input_sha256":"same","research_outcome_access_approved":True,
                "outcome_independently_verified":True,"candidate_pre_registered":True,
                "result":"1-2-3","forecasts":{"a":base,"b":dict(base,model_id="b")}}
    def test_identical_models_have_zero_paired_delta(self):
        o=compare([self.row()],"a","b")
        self.assertEqual(o["eligible_races"],1)
        self.assertEqual(o["metrics"]["top10"]["delta"],0)
        self.assertAlmostEqual(o["metrics"]["log_loss"]["delta"],0)
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
    def test_unapproved_outcome_rejected(self):
        r=self.row()
        r["research_outcome_access_approved"]=False
        self.assertEqual(compare([r],"a","b")["eligible_races"],0)

if __name__ == "__main__":
    unittest.main()
