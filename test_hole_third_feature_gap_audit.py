import unittest
from pathlib import Path
from unittest.mock import patch
from hole_third_feature_gap_audit import ticket_features,signed_gap,inspect
from test_hole_third_choice_research import archive

RATES=[5,3,8,7,6,1]
CODES=("202611030101","202611030102","202611030103","202611030104")


class ThirdFeatureGapTests(unittest.TestCase):
    def test_features_use_saved_donor_rank_score_and_rate(self):
        features=ticket_features(archive(),RATES)
        self.assertEqual(features["1-5-3"]["best_donor_rank"],2)
        self.assertEqual(features["1-5-3"]["max_donor_score"],6)
        self.assertEqual(features["1-5-3"]["national_rate"],8)
        self.assertEqual(signed_gap(5,4),"positive")
        self.assertEqual(signed_gap(3,4),"negative")
        self.assertEqual(signed_gap(4,4),"zero")
        self.assertEqual(signed_gap(None,4),"missing")

    def test_four_outcome_classes_reconcile_and_selection_precedes_results(self):
        a=archive()
        # Frozen national ranking chooses 1-5-3, 1-6-3.
        winners=("1-5-3","1-5-2","1-5-6","4-2-1")
        events=[]
        def get_archive(code,root):
            events.append(("archive",code))
            return 200,a
        def get_result(code,root):
            events.append(("result",code))
            return {"status":"historical_comparison_only",
                    "winning_ticket":winners[CODES.index(code)]}
        with patch("hole_third_feature_gap_audit.archived_four_modes",
                   side_effect=get_archive),patch(
             "hole_third_feature_gap_audit.national_rates",
             return_value=RATES),patch(
             "hole_third_feature_gap_audit.compare_race",
             side_effect=get_result):
            result=inspect(CODES,Path("."))
        self.assertEqual(result["comparable"],4)
        self.assertEqual(result["outcomes"],{
            "chosen_exact_hit":1,
            "selected_pair_wrong_third_donor_exact":1,
            "selected_pair_wrong_third_not_in_donor":1,
            "pair_not_selected":1})
        self.assertEqual(result["feature_gap_signs"]["national_rate"],{"positive":1})
        self.assertEqual(result["feature_gap_signs"]["max_donor_score"],{"positive":1})
        self.assertEqual(result["feature_gap_signs"]["best_donor_rank"],{"negative":1})
        self.assertEqual(len(result["examples"]),1)
        self.assertEqual(events,[
            ("archive",c) if i%2==0 else ("result",c)
            for c in CODES for i in (0,1)])

    def test_pending_result_not_counted(self):
        with patch("hole_third_feature_gap_audit.archived_four_modes",
                   return_value=(200,archive())),patch(
             "hole_third_feature_gap_audit.national_rates",return_value=RATES),patch(
             "hole_third_feature_gap_audit.compare_race",
             return_value={"status":"not_confirmed"}):
            result=inspect([CODES[0]],Path("."))
        self.assertEqual(result["comparable"],0)
        self.assertEqual(result["excluded"]["unconfirmed_result"],1)
        self.assertEqual(sum(result["outcomes"].values()),0)

    def test_absent_national_rates_are_missing_not_invented(self):
        f=ticket_features(archive(),None)
        self.assertIsNone(f["1-5-3"]["national_rate"])


if __name__=="__main__":
    unittest.main()
