import unittest
from pathlib import Path
from unittest.mock import patch

from hole_new_head_coverage_research import new_head_variants,inspect
from hole_pair_diversification_research import first_second
from test_hole_third_choice_research import archive as fixture

CODE="202611040101"
RATES=[5,3,8,7,6,1]


def with_new_heads():
    a=fixture()
    a["modes"]["hit"]["tickets"].extend([
        {"combo":"4-1-2","p":8},{"combo":"5-1-2","p":7},
        {"combo":"1-5-2","p":1}])
    a["modes"]["balance"]["tickets"].extend([
        {"combo":"4-1-3","p":6},{"combo":"5-1-3","p":5}])
    return a


class NewHeadCoverageTests(unittest.TestCase):
    def test_two_policies_preserve_frozen_prefix_budget_and_original_pairs(self):
        archive=with_new_heads()
        old=[r["combo"] for r in archive["modes"]["hole"]["tickets"][:10]]
        v=new_head_variants(archive,RATES)
        for name,tickets in v.items():
            with self.subTest(name=name):
                self.assertEqual(tickets[:5],old[:5])
                self.assertEqual(len(tickets),10)
                self.assertEqual(len(set(tickets)),10)
                self.assertTrue({first_second(t) for t in old}.issubset(
                    {first_second(t) for t in tickets}))
        self.assertTrue(any(t.startswith("4-") for t in v["one_new_head"]))
        self.assertTrue(any(t.startswith("1-5-") for t in v["one_new_head"]))
        self.assertEqual({t[0] for t in v["two_new_heads"] if t not in old},
                         {"4","5"})

    def test_missing_new_heads_fallback_is_unchanged(self):
        a=fixture();base=[t["combo"] for t in a["modes"]["hole"]["tickets"][:10]]
        v=new_head_variants(a,RATES)
        self.assertEqual(v["one_new_head"],base)
        self.assertEqual(v["two_new_heads"],base)

    def test_result_read_after_prediction_and_head_recovery_separately_counted(self):
        archive=with_new_heads();events=[]
        def source(code,root):
            events.append("source")
            return 200,archive
        def settled(code,root):
            events.append("settled")
            return {"status":"historical_comparison_only",
                    "winning_ticket":"4-1-3"}
        with patch("hole_new_head_coverage_research.archived_four_modes",
                   side_effect=source),patch(
             "hole_new_head_coverage_research.national_rates",
             return_value=RATES),patch(
             "hole_new_head_coverage_research.compare_race",
             side_effect=settled):
            report=inspect([CODE],Path("."))
        self.assertEqual(events,["source","settled"])
        self.assertEqual(report["comparable"],1)
        self.assertEqual(report["baseline_miss_reason"]["baseline_head_absent"],1)
        self.assertEqual(report["baseline_miss_reason"]["one_new_head_covered"],1)
        self.assertEqual(report["topn"]["one_new_head"]["top5"]["hits"],0)
        self.assertEqual(report["paired_vs_locked"]["one_new_head"]["net"],
                         report["topn"]["one_new_head"]["top10"]["hits"]-
                         report["topn"]["locked_two_pairs"]["top10"]["hits"])

    def test_unconfirmed_result_excluded(self):
        with patch("hole_new_head_coverage_research.archived_four_modes",
                   return_value=(200,with_new_heads())),patch(
             "hole_new_head_coverage_research.national_rates",
             return_value=RATES),patch(
             "hole_new_head_coverage_research.compare_race",
             return_value={"status":"pending"}):
            r=inspect([CODE],Path("."))
        self.assertEqual(r["comparable"],0)
        self.assertEqual(r["excluded"]["unconfirmed_result"],1)
        self.assertEqual(r["topn"]["two_new_heads"]["top10"]["hits"],0)


if __name__=="__main__":
    unittest.main()
