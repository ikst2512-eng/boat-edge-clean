import json
import unittest
from research_remote_pair_evidence import audit_pair_blob

class RemotePairEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.pair={"race_code":"202610281201","frozen_at_jst":"2026-10-28T09:00:00+09:00",
                   "cutoff_jst":"2026-10-28T09:20:00+09:00"}
        self.data=json.dumps(self.pair).encode()
        self.run={"event":"push","head_sha":"a"*40,
                  "head_branch":"research/paired-hit-evaluation-20261027",
                  "repository":{"full_name":"ikst2512-eng/boat-edge-clean"},
                  "created_at":"2026-10-28T00:05:00Z","id":99}
    def test_matching_blob_and_receipt(self):
        x=audit_pair_blob(self.data,"research_prospective_pairs/202610281201.json",
                          self.run,"a"*40,self.data)
        self.assertTrue(x["remote_pair_evidence"])
        self.assertFalse(x["prospective_hit_rate_verified"])
    def test_tampered_commit_blob_fails(self):
        x=audit_pair_blob(self.data,"research_prospective_pairs/202610281201.json",
                          self.run,"a"*40,b"other")
        self.assertFalse(x["remote_pair_evidence"])
    def test_wrong_race_path_rejected(self):
        with self.assertRaises(ValueError):
            audit_pair_blob(self.data,"research_prospective_pairs/202610281202.json",
                            self.run,"a"*40,self.data)
if __name__=="__main__":
    unittest.main()
