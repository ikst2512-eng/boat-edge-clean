import unittest
from pathlib import Path
from unittest.mock import patch

from hole_third_donor_ranking_research import select,rank_candidates,inspect
from test_hole_third_choice_research import archive as source_archive


CODE="202611040101"


def archive_with_consensus():
    archive=source_archive()
    archive["modes"]["balance"]["tickets"]=[
        {"combo":"1-5-3","p":3},{"combo":"1-6-3","p":2}]
    return archive


class DonorRankingResearchTests(unittest.TestCase):
    def test_consensus_and_first_hit_rank_choose_different_thirds(self):
        archive=archive_with_consensus()
        picks=select(archive,[5,3,8,7,6,1])
        self.assertEqual(picks["donor_order"][5:7],["1-5-2","1-6-2"])
        self.assertEqual(picks["donor_consensus"][5:7],["1-5-3","1-6-3"])
        self.assertEqual(picks["hit_rank_first"][5:7],["1-5-2","1-6-2"])
        for name,rows in picks.items():
            with self.subTest(name=name):
                self.assertEqual(rows[:5],picks["baseline"][:5])
                self.assertEqual(len(rows),10)
                self.assertEqual(len(set(rows)),10)

    def test_unchanged_baseline_does_not_invent_new_tickets(self):
        archive=source_archive()
        base=["1-2-3","1-3-4","1-2-4","1-3-5","1-4-2",
              "1-4-3","1-4-5","1-2-5","1-3-2","1-2-6"]
        frozen={"baseline":base,"donor_order":base}
        for method in ("donor_consensus","hit_rank_first"):
            self.assertEqual(rank_candidates(archive,frozen,method),base)

    def test_no_outcome_reaches_selector_and_gains_losses_reconcile(self):
        archive=archive_with_consensus()
        events=[]
        def freeze(a,rates):
            events.append("select")
            return select(a,rates)
        def result(code,root):
            events.append("result")
            return {"status":"historical_comparison_only",
                    "winning_ticket":"1-5-3"}
        with patch("hole_third_donor_ranking_research.archived_four_modes",
                   return_value=(200,archive)),patch(
             "hole_third_donor_ranking_research.national_rates",
             return_value=[5,3,8,7,6,1]),patch(
             "hole_third_donor_ranking_research.select",side_effect=freeze),patch(
             "hole_third_donor_ranking_research.compare_race",side_effect=result):
            output=inspect([CODE],Path("."))
        self.assertEqual(events,["select","result"])
        self.assertEqual(output["comparable"],1)
        self.assertEqual(output["topn"]["donor_consensus"]["top10"]["gained"],1)
        self.assertEqual(output["topn"]["donor_consensus"]["top10"]["lost"],0)
        self.assertEqual(output["topn"]["donor_consensus"]["top5"]["hits"],0)
        self.assertEqual(output["topn"]["hit_rank_first"]["top10"]["hits"],0)

    def test_unconfirmed_result_not_scored(self):
        archive=archive_with_consensus()
        with patch("hole_third_donor_ranking_research.archived_four_modes",
                   return_value=(200,archive)),patch(
             "hole_third_donor_ranking_research.national_rates",
             return_value=[5,3,8,7,6,1]),patch(
             "hole_third_donor_ranking_research.compare_race",
             return_value={"status":"unconfirmed"}):
            output=inspect([CODE],Path("."))
        self.assertEqual(output["comparable"],0)
        self.assertEqual(output["unavailable"],{"unconfirmed_result":1})
        self.assertEqual(output["topn"]["donor_consensus"]["top10"]["hits"],0)

    def test_methods_reject_unknown_names(self):
        with self.assertRaisesRegex(ValueError,"unknown_research_method"):
            rank_candidates(source_archive(),{"baseline":[],"donor_order":[]},"oracle")


if __name__=="__main__":
    unittest.main()
