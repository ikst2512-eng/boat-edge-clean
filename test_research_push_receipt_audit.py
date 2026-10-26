import unittest
from research_push_receipt_audit import audit_push_receipt

class PushReceiptTests(unittest.TestCase):
    def setUp(self):
        self.pair={"race_code":"202610281201","frozen_at_jst":"2026-10-28T09:00:00+09:00","cutoff_jst":"2026-10-28T09:20:00+09:00"}
        self.run={"event":"push","head_sha":"a"*40,"head_branch":"research/paired-hit-evaluation-20261027",
                  "repository":{"full_name":"ikst2512-eng/boat-edge-clean"},
                  "created_at":"2026-10-28T00:05:00Z","id":10}
    def test_server_timestamp_before_cutoff(self):
        self.assertTrue(audit_push_receipt(self.pair,self.run,"a"*40)["server_observed_pre_cutoff"])
    def test_wrong_sha_or_late_run(self):
        self.assertFalse(audit_push_receipt(self.pair,self.run,"b"*40)["server_observed_pre_cutoff"])
        self.run["created_at"]="2026-10-28T00:21:00Z"
        self.assertFalse(audit_push_receipt(self.pair,self.run,"a"*40)["server_observed_pre_cutoff"])
    def test_not_push_event(self):
        self.run["event"]="pull_request"
        self.assertFalse(audit_push_receipt(self.pair,self.run,"a"*40)["server_observed_pre_cutoff"])
if __name__=="__main__":
    unittest.main()
