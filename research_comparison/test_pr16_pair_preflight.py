import unittest
from paired_compare import TICKETS
from pr16_pair_preflight import inspect_pair

class PairPreflightTests(unittest.TestCase):
    def pair(self):
        p={t:1/120 for t in TICKETS}
        return dict(status="research_unvalidated",baseline=p,candidate=dict(p),
                    frozen_at_jst="2026-10-28T11:50:00+09:00",
                    cutoff_jst="2026-10-28T12:00:00+09:00",
                    source_snapshot_generated_at="2026-10-28T11:49:00+09:00",
                    prospective_verified=False,entry_status="assumed_identity_not_verified",
                    candidate_git_blob_sha="a"*40)
    def test_unscored_even_when_syntactically_valid(self):
        outcome=inspect_pair(self.pair())
        self.assertFalse(outcome["ready_for_scoring"])
        self.assertTrue(outcome["distribution_structure_valid"])
    def test_corrupt_distribution_rejected(self):
        pair=self.pair()
        pair["candidate"]["1-2-3"]=-1
        outcome=inspect_pair(pair)
        self.assertFalse(outcome["distribution_structure_valid"])
    def test_late_freeze_rejected(self):
        pair=self.pair()
        pair["frozen_at_jst"]=pair["cutoff_jst"]
        self.assertIn("inconsistent pre-cutoff chronology",inspect_pair(pair)["reasons"])

if __name__=="__main__":
    unittest.main()
