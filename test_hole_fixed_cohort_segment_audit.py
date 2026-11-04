"""Deterministic frozen-cohort and result-blind comparison gate."""
import unittest
from unittest.mock import patch
import hole_fixed_cohort_segment_audit as audit

class HoleFixedCohortTest(unittest.TestCase):
    def test_cohort_is_frozen_and_deduplicated(self):
        codes = audit.fixed_codes()
        self.assertEqual(len(codes), 120)
        self.assertEqual(len(set(codes)),120)
        self.assertEqual(codes[0],"202610280101")
        self.assertEqual(codes[-1],"202611042401")
        older = audit.original_codes()
        self.assertEqual(len(older),120)
        self.assertEqual(len(set(older)&set(codes)),86)

    def test_result_is_opened_after_proposals(self):
        events=[]
        base=["1-2-3","1-2-4","1-3-4","1-3-2","1-4-2",
              "1-4-3","1-5-2","1-5-3","1-6-2","1-6-3"]
        fake={"model_version":"CLEAN_FOUR_MODES_V1_UNCALIBRATED",
              "modes":{"hole":{"tickets":[{"combo":c} for c in base]}}}
        def select(_):
            events.append("proposals")
            return {name:list(base) for name in audit.POLICIES}
        def outcome(*_):
            events.append("result")
            return {"status":"historical_comparison_only","winning_ticket":"1-2-3"}
        with patch.object(audit,"archived_four_modes",return_value=(200,fake)), \
             patch.object(audit,"frozen_proposals",side_effect=select), \
             patch.object(audit,"compare_race",side_effect=outcome):
            row=audit.compare_one("202610280101",".")
        self.assertEqual(events,["proposals","result"])
        self.assertEqual(row["ranks"],{"baseline":1,"same_pair":1,"two_pairs":1})
        self.assertTrue(row["top1_head_match"])

    def test_invalid_archive_never_opens_outcome(self):
        with patch.object(audit,"archived_four_modes",return_value=(404,None)), \
             patch.object(audit,"compare_race",side_effect=AssertionError("early read")):
            with self.assertRaisesRegex(ValueError,"invalid_archived_forecast"):
                audit.compare_one("202610280101",".")

    def test_miss_definitions_and_attribution(self):
        rows=[
            {"ranks":{"baseline":0,"same_pair":6,"two_pairs":0},
             "changed":{"baseline":False,"same_pair":True,"two_pairs":False},
             "top1_head_match":True,"head_in_top10":True,
             "baseline_miss_top10":"winner_second_pair_absent",
             "baseline_miss_full_hole":"covered"},
            {"ranks":{"baseline":7,"same_pair":9,"two_pairs":0},
             "changed":{"baseline":False,"same_pair":True,"two_pairs":True},
             "top1_head_match":False,"head_in_top10":True,
             "baseline_miss_top10":"covered",
             "baseline_miss_full_hole":"covered"},
        ]
        r=audit.summarize(rows)
        self.assertEqual(r["policies"]["baseline"]["hits"]["top10"],1)
        self.assertEqual(r["policies"]["same_pair"]["hits"]["top10"],2)
        self.assertEqual(r["policies"]["same_pair"]["gain"]["top10"],1)
        self.assertEqual(r["policies"]["two_pairs"]["loss"]["top10"],1)
        self.assertEqual(r["policies"]["same_pair"]["existing_hits_rank_worse"],1)
        self.assertEqual(r["baseline_misses_top10"]["winner_second_pair_absent"],1)
        self.assertEqual(r["baseline_misses_full_hole"]["covered"],2)

if __name__=="__main__":
    unittest.main()
