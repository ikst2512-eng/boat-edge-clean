import unittest
from ai_frozen_race_preflight import preflight

class PreflightTests(unittest.TestCase):
    def test_known_archive_research_only(self):
        result = preflight("202610280101")
        self.assertEqual(result["status"], "historical_comparison_only")
        self.assertEqual(result["winning_ticket"], "4-1-3")
        self.assertFalse(result["formal"])
        self.assertFalse(result["production_change_allowed"])
    def test_missing_and_unverified_evidence_not_approved(self):
        for case in ({"status":"historical_comparison_only","formal":True,"remote_first_seen_verified":False},
                     {"status":"historical_comparison_only","formal":False,"remote_first_seen_verified":True},
                     {"status":"result_unavailable","formal":False}):
            verdict = preflight("202610280101", comparator=lambda code: case)
            self.assertNotEqual(verdict["status"], "historical_comparison_only")
    def test_bad_code_rejected_without_source_call(self):
        result = preflight("../bad", comparator=lambda code: self.fail("called"))
        self.assertEqual(result["status"], "invalid_code")

if __name__=="__main__":
    unittest.main()
