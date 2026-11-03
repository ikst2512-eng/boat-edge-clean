import unittest
from pathlib import Path
from unittest.mock import patch

from hole_third_donor_ranking_research import select,rank_candidates,inspect,paired_outcomes,describe_disagreement
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

    def test_paired_results_preserve_race_denominator_and_date_partition(self):
        def row(code,national,consensus):
            return {"race_code":code,"flags":{
                "third_national_rate":{"top10":national},
                "donor_consensus":{"top10":consensus}}}
        data=[
            row("202611040101",True,True),
            row("202611040102",True,False),
            row("202611040103",False,True),
            row("202611050101",True,False),
            row("202611050102",False,False)]
        paired=paired_outcomes(data)
        self.assertEqual(paired["sample"],5)
        self.assertEqual(paired["both_hit"],1)
        self.assertEqual(paired["only_challenger"],2)
        self.assertEqual(paired["only_comparator"],1)
        self.assertEqual(paired["neither_hit"],1)
        self.assertEqual(paired["net"],1)
        self.assertEqual(paired["dates"]["20261104"]["races"],3)
        self.assertEqual(paired["dates"]["20261105"]["races"],2)
        self.assertEqual(paired["disagreement_race_codes"],
                         ["202611040102","202611040103","202611050101"])

    def test_paired_comparison_rejects_invalid_hit_booleans(self):
        data=[{"race_code":CODE,"flags":{
            "third_national_rate":{"top10":1},
            "donor_consensus":{"top10":False}}}]
        with self.assertRaisesRegex(ValueError,"invalid_hit_boolean"):
            paired_outcomes(data)
        with self.assertRaisesRegex(ValueError,"unknown_comparison"):
            paired_outcomes([],challenger="outcome_oracle")

    def test_actual_inspection_emits_paired_audit_consistent_with_hits(self):
        archive=archive_with_consensus()
        with patch("hole_third_donor_ranking_research.archived_four_modes",
                   return_value=(200,archive)),patch(
             "hole_third_donor_ranking_research.national_rates",
             return_value=[5,3,8,7,6,1]),patch(
             "hole_third_donor_ranking_research.compare_race",
             return_value={"status":"historical_comparison_only",
                           "winning_ticket":"1-5-3"}):
            output=inspect([CODE],Path("."))
        paired=output["paired_top10"]["donor_consensus"]
        self.assertEqual(paired["sample"],output["comparable"])
        self.assertEqual(paired["net"],
                         output["topn"]["third_national_rate"]["top10"]["hits"]-
                         output["topn"]["donor_consensus"]["top10"]["hits"])

    def test_disagreement_explains_both_directions_without_touching_selector(self):
        archive=archive_with_consensus()
        picks=select(archive,[5,3,8,7,6,1])
        national=describe_disagreement(CODE,"1-5-3",archive,
                                      [5,3,8,7,6,1],picks)
        self.assertIsNone(national)  # Both national and consensus picked 1-5-3.
        consensus_only=describe_disagreement(CODE,"1-5-2",archive,
                                            [5,3,8,7,6,1],picks)
        self.assertEqual(consensus_only["category"],"consensus_only") if (
            "1-5-2" in picks["donor_consensus"] and
            "1-5-2" not in picks["third_national_rate"]) else self.assertIsNone(consensus_only)

    def test_features_preserve_frozen_rank_and_score(self):
        archive=archive_with_consensus()
        picks=select(archive,[5,3,8,7,6,1])
        # Modify selected candidates without deriving them from any result,
        # so each side wins one synthetic race under identical frozen inputs.
        altered={**picks,"third_national_rate":picks["donor_order"]}
        disagreement=describe_disagreement(CODE,"1-5-3",archive,
                                           [5,3,8,7,6,1],altered)
        self.assertEqual(disagreement["category"],"consensus_only")
        self.assertEqual(disagreement["winning_third_national_win_rate"],8)
        self.assertEqual(disagreement["winning_ticket_donor"]["donor_rank_1based"]["hit"],2)
        self.assertEqual(disagreement["winning_ticket_donor"]["donor_rank_1based"]["balance"],1)
        self.assertTrue(disagreement["winning_ticket_donor"]["present_in_both_donors"])
        self.assertEqual(disagreement["national_same_pair"][0]["ticket"],"1-5-2")
        self.assertEqual(disagreement["consensus_same_pair"][0]["ticket"],"1-5-3")
        inverse={**picks,"donor_consensus":picks["donor_order"]}
        other=describe_disagreement(CODE,"1-5-3",archive,
                                    [5,3,8,7,6,1],inverse)
        self.assertEqual(other["category"],"national_only")

    def test_inspection_disagreement_cases_equal_paired_discordance(self):
        archive=archive_with_consensus()
        picks=select(archive,[5,3,8,7,6,1])
        with patch("hole_third_donor_ranking_research.archived_four_modes",
                   return_value=(200,archive)),patch(
             "hole_third_donor_ranking_research.national_rates",
             return_value=[5,3,8,7,6,1]),patch(
             "hole_third_donor_ranking_research.select",
             return_value={**picks,"third_national_rate":picks["donor_order"]}),patch(
             "hole_third_donor_ranking_research.compare_race",
             return_value={"status":"historical_comparison_only",
                           "winning_ticket":"1-5-3"}):
            out=inspect([CODE],Path("."))
        self.assertEqual(len(out["disagreement_cases"]),1)
        self.assertEqual(out["disagreement_cases"][0]["category"],"consensus_only")
        paired=out["paired_top10"]["donor_consensus"]
        self.assertEqual(len(out["disagreement_cases"]),
                         paired["only_challenger"]+paired["only_comparator"])

    def test_methods_reject_unknown_names(self):
        with self.assertRaisesRegex(ValueError,"unknown_research_method"):
            rank_candidates(source_archive(),{"baseline":[],"donor_order":[]},"oracle")


if __name__=="__main__":
    unittest.main()
