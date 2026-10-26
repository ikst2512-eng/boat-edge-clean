import unittest
from snapshot_preflight import inspect, TICKETS

class SnapshotPreflightTests(unittest.TestCase):
    def test_top10_only_fails_closed(self):
        record={"status":"research","predictions":sorted(TICKETS)[:10]}
        result=inspect(record)
        self.assertFalse(result["ready"])
        self.assertIn("top10 only",result["reason"])
    def test_full_probabilities_still_require_provenance(self):
        tickets=sorted(TICKETS)
        record={"status":"research","predictions":tickets[:10],
                "probabilities":{k:1/120 for k in tickets}}
        result=inspect(record)
        self.assertFalse(result["ready"])
        self.assertIn("independent",result["reason"])
    def test_bad_top10_rejected(self):
        result=inspect({"status":"research","predictions":["1-2-3"]*10})
        self.assertFalse(result["ready"])
        self.assertEqual(result["reason"],"invalid top10 snapshot")

if __name__=="__main__":
    unittest.main()
