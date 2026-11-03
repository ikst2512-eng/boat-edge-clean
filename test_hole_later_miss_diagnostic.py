import unittest
from unittest.mock import patch
from hole_later_miss_diagnostic import diagnose
class DiagnoseTests(unittest.TestCase):
    def test_separates_head_pair_and_third(self):
        outcome={"status":"historical_comparison_only","winning_ticket":"1-2-3",
           "modes":{"hole":{"coverage_diagnostic":"winner_second_pair_absent"},
                    "hit":{"coverage_diagnostic":"covered"},
                    "balance":{"coverage_diagnostic":"winner_third_absent"}}}
        archive={"modes":{
           "hole":{"tickets":[{"combo":"1-4-3"}]},
           "hit":{"tickets":[{"combo":"1-2-3"}]},
           "balance":{"tickets":[{"combo":"1-2-4"}]}}}
        with patch("hole_later_miss_diagnostic.compare_race",return_value=outcome),patch(
             "hole_later_miss_diagnostic.archived_four_modes",return_value=(200,archive)):
            r=diagnose(["202611020101"],".")
        self.assertEqual(r["misses"]["hole"]["winner_second_pair_absent"],1)
        self.assertEqual(r["donor_winning_coverage"]["hit_full"],1)
        self.assertEqual(r["donor_winning_coverage"]["balance_pair"],1)
        self.assertEqual(r["donor_winning_coverage"]["balance_full"],0)
    def test_invalid_archive_fails(self):
        with patch("hole_later_miss_diagnostic.compare_race",return_value={"status":"invalid"}),patch(
             "hole_later_miss_diagnostic.archived_four_modes",return_value=(404,{})):
            with self.assertRaises(ValueError): diagnose(["202611020101"],".")
if __name__=="__main__": unittest.main()
