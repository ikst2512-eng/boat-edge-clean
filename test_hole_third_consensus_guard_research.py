import unittest
from pathlib import Path
from unittest.mock import patch

from hole_third_consensus_guard_research import guarded,inspect
from hole_third_donor_ranking_research import select
from test_hole_third_donor_ranking_research import archive_with_consensus

CODE="202611040101"
RATES=[5,3,8,7,6,1]

class GuardResearchTests(unittest.TestCase):
    def test_consensus_guard_substitutes_only_with_both_top_two_and_small_rate_gap(self):
        archive=archive_with_consensus()
        picks=select(archive,RATES)
        # 1-5-3 has hit rank2, balance rank1; 1-5-2 has national
        # third rate 3 vs consensus third rate 8, so guard may choose consensus.
        national=picks["third_national_rate"]
        altered={**picks,"third_national_rate":picks["donor_order"]}
        guarded_picks=guarded(archive,RATES,altered)
        self.assertEqual(guarded_picks[5],"1-5-3")
        self.assertEqual(guarded_picks[:5],national[:5])
        self.assertEqual(len(guarded_picks),10)
        self.assertEqual(len(set(guarded_picks)),10)

    def test_large_national_advantage_keeps_national_ticket(self):
        archive=archive_with_consensus()
        picks=select(archive,RATES)
        altered={**picks,"third_national_rate":picks["donor_order"]}
        reversed_rates=[5,10,1,7,6,1]
        current=guarded(archive,reversed_rates,altered)
        self.assertEqual(current[5],"1-5-2")

    def test_missing_rates_keeps_locked_choice(self):
        archive=archive_with_consensus()
        picks=select(archive,RATES)
        self.assertEqual(guarded(archive,None,picks),
                         picks["third_national_rate"])

    def test_result_access_after_selection_and_counts_reconcile(self):
        archive=archive_with_consensus()
        event=[]
        def choose(a,r):
            event.append("select")
            picks=select(a,r)
            return {**picks,"third_national_rate":picks["donor_order"]}
        def result(code,root):
            event.append("result")
            return {"status":"historical_comparison_only",
                    "winning_ticket":"1-5-3"}
        with patch("hole_third_consensus_guard_research.archived_four_modes",
                   return_value=(200,archive)),patch(
             "hole_third_consensus_guard_research.national_rates",
             return_value=RATES),patch(
             "hole_third_consensus_guard_research.select",side_effect=choose),patch(
             "hole_third_consensus_guard_research.compare_race",side_effect=result):
            out=inspect([CODE],Path("."))
        self.assertEqual(event,["select","result"])
        self.assertEqual(out["comparable"],1)
        self.assertEqual(out["guard_changed_races"],1)
        self.assertEqual(out["topn"]["consensus_guard"]["top10"]["hits"],1)
        self.assertEqual(out["topn"]["consensus_guard"]["top5"]["hits"],0)
        self.assertEqual(out["paired_guard_vs_national"]["only_challenger"],1)

    def test_no_confirmed_result_never_scored(self):
        archive=archive_with_consensus()
        with patch("hole_third_consensus_guard_research.archived_four_modes",
                   return_value=(200,archive)),patch(
             "hole_third_consensus_guard_research.national_rates",
             return_value=RATES),patch(
             "hole_third_consensus_guard_research.compare_race",
             return_value={"status":"pending"}):
            out=inspect([CODE],Path("."))
        self.assertEqual(out["comparable"],0)
        self.assertEqual(out["unavailable"],{"unconfirmed_result":1})
        self.assertEqual(out["topn"]["consensus_guard"]["top10"]["hits"],0)

if __name__=="__main__":
    unittest.main()
