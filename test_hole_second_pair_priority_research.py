import unittest
from pathlib import Path
from unittest.mock import patch

from hole_second_pair_priority_research import propose,inspect
from test_hole_third_choice_research import archive as fixture

CODE="202611040101"


def pair_fixture():
    a=fixture()
    a["modes"]["hit"]["tickets"]=[
        {"combo":"1-5-2","p":10},
        {"combo":"1-5-3","p":9},
        {"combo":"1-6-2","p":5},
        {"combo":"1-6-3","p":4}]
    a["modes"]["balance"]["tickets"]=[
        {"combo":"1-6-2","p":7},
        {"combo":"1-6-3","p":6},
        {"combo":"1-3-6","p":4}]
    return a


class PairResearchTests(unittest.TestCase):
    def test_candidates_keep_top5_budget_existing_pairs(self):
        archive=pair_fixture()
        base=[t["combo"] for t in archive["modes"]["hole"]["tickets"][:10]]
        for policy in ("pair_max_score","pair_donor_consensus"):
            with self.subTest(policy=policy):
                out=propose(archive,[5,3,8,7,6,1],policy)
                self.assertEqual(out[:5],base[:5])
                self.assertEqual(len(out),10)
                self.assertEqual(len(set(out)),10)
                self.assertEqual(set(tuple(x.split("-")[:2]) for x in base)-
                                 set(tuple(x.split("-")[:2]) for x in out),set())
                self.assertEqual(set(tuple(x.split("-")[:2]) for x in out)-
                                 set(tuple(x.split("-")[:2]) for x in base),
                                 {("1","5"),("1","6")})

    def test_scores_choose_third_without_using_result(self):
        a=pair_fixture()
        out=propose(a,[5,3,8,7,6,1],"pair_max_score")
        self.assertIn("1-5-3",out)
        self.assertIn("1-6-3",out)

    def test_unknown_policy_rejected(self):
        with self.assertRaises(ValueError):
            propose(pair_fixture(),None,"result_oracle")

    def test_lack_of_two_new_pairs_keeps_old_tickets(self):
        a=pair_fixture()
        a["modes"]["hit"]["tickets"]=a["modes"]["hit"]["tickets"][:2]
        a["modes"]["balance"]["tickets"]=[]
        base=[t["combo"] for t in a["modes"]["hole"]["tickets"][:10]]
        self.assertEqual(propose(a,None,"pair_max_score"),base)

    def test_selection_runs_before_result_and_paired_metrics_reconcile(self):
        a=pair_fixture();calls=[]
        def get_result(code,root):
            calls.append("result")
            return {"status":"historical_comparison_only",
                    "winning_ticket":"1-5-3"}
        def get_archive(code,root):
            calls.append("archive")
            return 200,a
        with patch("hole_second_pair_priority_research.archived_four_modes",
                   side_effect=get_archive),patch(
             "hole_second_pair_priority_research.national_rates",
             return_value=[5,3,8,7,6,1]),patch(
             "hole_second_pair_priority_research.compare_race",
             side_effect=get_result):
            result=inspect([CODE],Path("."))
        self.assertEqual(calls,["archive","result"])
        self.assertEqual(result["comparable"],1)
        self.assertEqual(result["topn"]["pair_max_score"]["top5"]["hits"],0)
        self.assertEqual(
            result["paired_vs_locked"]["pair_max_score"]["net"],
            result["topn"]["pair_max_score"]["top10"]["hits"]-
            result["topn"]["third_national_rate"]["top10"]["hits"])

    def test_unconfirmed_result_excluded(self):
        with patch("hole_second_pair_priority_research.archived_four_modes",
                   return_value=(200,pair_fixture())),patch(
             "hole_second_pair_priority_research.national_rates",return_value=None),patch(
             "hole_second_pair_priority_research.compare_race",
             return_value={"status":"result_pending"}):
            result=inspect([CODE],Path("."))
        self.assertEqual(result["comparable"],0)
        self.assertEqual(result["unavailable"],{"unconfirmed_result":1})


if __name__=="__main__":
    unittest.main()
