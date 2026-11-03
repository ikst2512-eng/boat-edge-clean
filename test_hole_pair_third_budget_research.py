import unittest
from pathlib import Path
from unittest.mock import patch

from hole_pair_third_budget_research import one_pair_two_thirds,inspect
from hole_pair_diversification_research import first_second
from test_hole_third_choice_research import archive as fixture

CODE="202611040101"
RATES=[5,3,8,7,6,1]


class BudgetResearchTests(unittest.TestCase):
    def test_one_pair_two_thirds_preserves_top5_budget_and_original_pairs(self):
        a=fixture()
        old=[t["combo"] for t in a["modes"]["hole"]["tickets"][:10]]
        out=one_pair_two_thirds(a,RATES)
        self.assertEqual(out[:5],old[:5])
        self.assertEqual(len(out),10)
        self.assertEqual(len(set(out)),10)
        self.assertEqual(len(set(out)-set(old)),2)
        self.assertEqual({first_second(t) for t in out if t not in old},
                         {("1","5")})
        self.assertTrue({first_second(t) for t in old}.issubset(
            {first_second(t) for t in out}))
        self.assertEqual({t for t in out if t not in old},
                         {"1-5-3","1-5-4"})

    def test_no_candidate_pair_with_two_thirds_keeps_baseline(self):
        a=fixture()
        a["modes"]["hit"]["tickets"]=[
            {"combo":"1-5-2","p":1},{"combo":"1-6-2","p":2}]
        a["modes"]["balance"]["tickets"]=[]
        base=[x["combo"] for x in a["modes"]["hole"]["tickets"][:10]]
        self.assertEqual(one_pair_two_thirds(a,RATES),base)

    def test_result_is_read_only_after_both_selectors(self):
        a=fixture();events=[]
        def original(code,root):
            events.append("archive")
            return 200,a
        def result(code,root):
            events.append("result")
            return {"status":"historical_comparison_only",
                    "winning_ticket":"1-5-4"}
        with patch("hole_pair_third_budget_research.archived_four_modes",
                   side_effect=original),patch(
             "hole_pair_third_budget_research.national_rates",
             return_value=RATES),patch(
             "hole_pair_third_budget_research.compare_race",
             side_effect=result):
            data=inspect([CODE],Path("."))
        self.assertEqual(events,["archive","result"])
        self.assertEqual(data["comparable"],1)
        self.assertEqual(data["topn"]["one_pair_two_thirds"]["top10"]["hits"],1)
        self.assertEqual(data["topn"]["one_pair_two_thirds"]["top5"]["hits"],0)
        self.assertEqual(data["one_pair_vs_two_pairs"]["only_one_pair"],1)
        self.assertEqual(data["one_pair_vs_two_pairs"]["net"],1)

    def test_unconfirmed_does_not_inflate_hits(self):
        with patch("hole_pair_third_budget_research.archived_four_modes",
                   return_value=(200,fixture())),patch(
             "hole_pair_third_budget_research.national_rates",return_value=RATES),patch(
             "hole_pair_third_budget_research.compare_race",
             return_value={"status":"pending"}):
            result=inspect([CODE],Path("."))
        self.assertEqual(result["comparable"],0)
        self.assertEqual(result["unavailable"]["unconfirmed_result"],1)
        self.assertEqual(result["topn"]["one_pair_two_thirds"]["top10"]["hits"],0)


if __name__=="__main__":
    unittest.main()
