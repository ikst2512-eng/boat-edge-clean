import unittest
from pathlib import Path
from unittest.mock import patch

from hole_third_full_denominator_audit import candidates,inspect
from test_hole_third_choice_research import archive as archive_fixture

CODES=("202611030101","202611030102","202611030103","202611030104")
RATES=[5,3,8,7,6,1]


class FullDenominatorAuditTests(unittest.TestCase):
    def test_real_selectors_keep_same_pairs_and_top5(self):
        a=archive_fixture()
        variants=candidates(a,RATES)
        base=variants["baseline"]
        pairs=[{tuple(t.split("-")[:2]) for t in picks}
               for picks in variants.values()]
        self.assertTrue(all(p==pairs[0] for p in pairs))
        self.assertEqual({len(x) for x in variants.values()},{10})
        self.assertTrue(all(x[:5]==base[:5] for x in variants.values()))

    def test_conditional_and_full_denominators_and_paired_reconcile(self):
        a=archive_fixture()
        frozen=candidates(a,RATES)
        # Use distinct winning tickets to cover locked new pair, old pair,
        # and absent pair. All variants are locked before result access.
        winners=["1-5-3","1-2-3","4-2-1","1-5-2"]
        events=[]
        def selection(archive,rates):
            events.append("select")
            return frozen
        def result(code,root):
            events.append("result")
            return {"status":"historical_comparison_only",
                    "winning_ticket":winners[CODES.index(code)]}
        with patch("hole_third_full_denominator_audit.archived_four_modes",
                   return_value=(200,a)), patch(
             "hole_third_full_denominator_audit.national_rates",
             return_value=RATES), patch(
             "hole_third_full_denominator_audit.candidates",
             side_effect=selection), patch(
             "hole_third_full_denominator_audit.compare_race",
             side_effect=result):
            stats=inspect(CODES,Path("."))
        self.assertEqual(events,["select","result"]*len(CODES))
        self.assertEqual(stats["comparable"],4)
        for policy in stats["top10_all_races"]:
            n=sum(v[policy]["races"] for v in
                  stats["correct_pair_condition"].values())
            self.assertEqual(n,4)
            hits=sum(v[policy].get("hits",0) for v in
                     stats["correct_pair_condition"].values())
            self.assertEqual(hits,stats["top10_all_races"][policy].get("hits",0))
        group=stats["correct_pair_condition"]
        self.assertEqual(group["prior_pair_already_covered"]["baseline"]["races"],1)
        self.assertEqual(group["winning_pair_not_covered"]["baseline"]["races"],1)
        self.assertEqual(group["new_pair_selected"]["baseline"]["races"],2)
        for name,metrics in stats["paired_against_national"].items():
            self.assertEqual(metrics["net"],
                stats["top10_all_races"][name]["hits"]-
                stats["top10_all_races"]["third_national_rate"]["hits"])

    def test_pending_results_are_excluded_from_numerator_and_denominator(self):
        with patch("hole_third_full_denominator_audit.archived_four_modes",
                   return_value=(200,archive_fixture())), patch(
             "hole_third_full_denominator_audit.national_rates",
             return_value=RATES), patch(
             "hole_third_full_denominator_audit.compare_race",
             return_value={"status":"result_pending"}):
            result=inspect([CODES[0]],Path("."))
        self.assertEqual(result["comparable"],0)
        self.assertEqual(result["unavailable"],{"unconfirmed_result":1})
        self.assertEqual(result["top10_all_races"]["third_national_rate"],{})

    def test_rejects_invalid_budget_before_reading_outcome(self):
        a=archive_fixture()
        frozen=candidates(a,RATES)
        frozen["donor_consensus"]=frozen["donor_consensus"][:9]
        with patch("hole_third_full_denominator_audit.archived_four_modes",
                   return_value=(200,a)), patch(
             "hole_third_full_denominator_audit.national_rates",
             return_value=RATES), patch(
             "hole_third_full_denominator_audit.select",
             return_value={**frozen,"donor_order":frozen["third_national_rate"]}):
            with self.assertRaisesRegex(ValueError,"invalid_frozen_pair_or_budget"):
                candidates(a,RATES)


if __name__=="__main__":
    unittest.main()
