import unittest
from research_third_party_payouts import parse_payouts_csv

class PayoutsTests(unittest.TestCase):
    def test_valid_and_duplicate_race_fail_closed(self):
        csv="レースコード,3連単_組番\n202610270102,1-2-4\n202610270103,3-6-4\n202610270103,2-1-3\n"
        report=parse_payouts_csv(csv)
        self.assertEqual(report["matched_payout_rows"],1)
        self.assertEqual(report["results"][0]["ticket"],"1-2-4")
        self.assertEqual(report["results"][0]["source_kind"],"third_party")
        self.assertEqual(report["excluded"]["duplicate_race_code"],1)
    def test_missing_columns(self):
        with self.assertRaises(ValueError):
            parse_payouts_csv("レースコード,違う列\n202610270102,1-2-4")
if __name__=="__main__":
    unittest.main()
