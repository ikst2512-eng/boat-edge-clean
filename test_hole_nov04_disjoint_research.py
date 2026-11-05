"""Research-only Nov 4 disjoint cohort tests."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import hole_nov04_disjoint_research as nov04

class Nov04DisjointTest(unittest.TestCase):
    def test_drift_or_missing_files_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            (root/"four_mode_forecasts").mkdir()
            (root/"confirmed_results").mkdir()
            with self.assertRaisesRegex(ValueError, "nov04_cohort_membership_drift"):
                nov04.select_codes(root)

    def test_deterministic_nonoverlap_and_pending_exclusion(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            forecasts=root/"four_mode_forecasts"
            results=root/"confirmed_results"
            forecasts.mkdir(); results.mkdir()
            for code in ("202611040101","202611040103","202611040104"):
                (forecasts/(code+".json")).write_text("{}",encoding="utf-8")
            for code in ("202611040101","202611040103"):
                (results/(code+".json")).write_text("{}",encoding="utf-8")
            with patch.object(nov04,"EXPECTED_PAIR_COHORT_SIZE",1), \
                 patch.object(nov04,"EXPECTED_PAIRED_BEFORE_EXCLUSION",2):
                selected, counts=nov04.select_codes(root)
            self.assertEqual(selected,["202611040103"])
            self.assertEqual(counts["result_file_absent"],1)
            self.assertEqual(counts["already_in_prior_cohort"],1)

    def test_summary_separates_top1_head_and_top1_ticket(self):
        row={"ranks":{"baseline":0,"same_pair":6,"two_pairs":0},
             "changed":{"baseline":False,"same_pair":True,"two_pairs":False},
             "top1_head_match":True,"head_in_top10":True,
             "baseline_miss_top10":"winner_second_pair_absent",
             "baseline_miss_full_hole":"winner_second_pair_absent"}
        from hole_fixed_cohort_segment_audit import summarize
        result=summarize([row])
        self.assertEqual(result["top1_head_matches"],1)
        self.assertEqual(result["policies"]["baseline"]["hits"]["top1"],0)
        self.assertEqual(result["policies"]["same_pair"]["hits"]["top10"],1)

if __name__=="__main__":
    unittest.main()
