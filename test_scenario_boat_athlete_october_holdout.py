"""Synthetic no-leakage tests for K92 boat/roster historical comparison."""
import copy
import math
import unittest

from scenario_boat_athlete_october_holdout import (
    ID,TICKETS,fit_training,predict_boat120,evaluate_october
)


def rows(month,n,reverse=False):
    data=[]
    for i in range(n):
        venue=f"{i%4+1:02d}"
        player=(i%7)+4001
        roster=(str(player), "4902","4903","4904","4905","4906")
        # The target finish is intentionally NOT passed to predict_boat120.
        ticket=((2,1,4) if i%5==0 else
                (1,3,2) if i%5==1 else
                (3,1,5) if i%5==2 else
                (1,2,3) if i%5==3 else (4,2,1))
        if reverse:
            ticket=tuple(reversed(ticket))
        data.append({"day":f"2026{month:02d}{i%25+1:02d}",
                     "venue":venue,"roster":roster,"ticket":ticket})
    return data


class HistoricalBoatAthleteTests(unittest.TestCase):
    def setUp(self):
        self.training=rows(8,300)+rows(9,150)
        self.october=rows(10,100)
        self.fitted=fit_training(self.training)

    def test_all_120_sum_and_three_model_shapes(self):
        board=predict_boat120(self.fitted,"01",self.october[0]["roster"])
        self.assertEqual(set(board),{"global_direct","venue_direct","venue_plus_athlete","global_plus_athlete"})
        for v in board.values():
            self.assertEqual(set(v),set(TICKETS))
            self.assertTrue(math.isclose(sum(v.values()),1,abs_tol=1e-9))
            self.assertGreater(min(v.values()),0)

    def test_october_label_change_cannot_affect_historical_prediction(self):
        first=copy.deepcopy(self.october)
        other=copy.deepcopy(self.october)
        other[0]["ticket"]=(6,5,4)
        a=predict_boat120(self.fitted,first[0]["venue"],first[0]["roster"])
        b=predict_boat120(self.fitted,other[0]["venue"],other[0]["roster"])
        self.assertEqual(a,b)
        self.assertTrue(self.fitted["never_trained_on_october"])
        self.assertNotIn("ticket",predict_boat120.__code__.co_varnames[:3])

    def test_train_only_and_known_pre_race_fields_historical_evaluation(self):
        result=evaluate_october(self.fitted,self.october,require_n=100)
        self.assertEqual(result["train_n"],450)
        self.assertEqual(result["holdout_n"],100)
        self.assertEqual(result["study_id"],ID)
        self.assertEqual(result["input_used_for_october_prediction"],
                         ["venue_code","boat_number","athlete_registration"])
        self.assertFalse(result["adoption_checks"]["true_predeadline_roster_source_certified"])
        self.assertTrue(result["historical_clean_six_finishers_selected_after_result"])
        self.assertFalse(result["production_adoption_allowed"])
        self.assertFalse(result["trained_on_october_labels"])
        self.assertIn("global_athlete_vs_global_delta",result)
        self.assertEqual(sum(result["paired_topn"]["global_athlete_vs_global"][10].values()),100)
        for m in result["models"].values():
            self.assertEqual(m["n"],100)
            self.assertGreaterEqual(m["top10"],m["top5"])
            self.assertGreaterEqual(m["top5"],m["top3"])
        self.assertEqual(sum(result["paired_topn"]["athlete_vs_venue"][10].values()),100)
        self.assertEqual(result["day_diagnostic"]["total_days"],25)
        self.assertEqual(sum(v["n"] for v in result["venue_diagnostic"].values()),100)
        self.assertEqual(sum(result["known_training_athletes_in_october_roster_distribution"].values()),100)
        self.assertEqual(len(result["global_athlete_vs_global_top10_pctpoint_day_bootstrap_95"]),2)

    def test_tampered_periods_or_labels_rejected(self):
        bad=copy.deepcopy(self.training)
        bad[0]["day"]="20261014"
        with self.assertRaises(ValueError):
            fit_training(bad)
        bad=copy.deepcopy(self.october)
        bad[0]["day"]="20260930"
        with self.assertRaises(ValueError):
            evaluate_october(self.fitted,bad)
        bad=copy.deepcopy(self.october)
        bad[0]["ticket"]=(1,1,2)
        with self.assertRaises(ValueError):
            evaluate_october(self.fitted,bad)
        bad=copy.deepcopy(self.october)
        bad[0]["roster"]=("4902",)*6
        with self.assertRaises(ValueError):
            evaluate_october(self.fitted,bad)

    def test_candidate_ranking_changes_only_with_athlete_prior(self):
        roster=self.october[0]["roster"]
        src=predict_boat120(self.fitted,"01",roster)
        changed=tuple(["4999",*roster[1:]])
        nxt=predict_boat120(self.fitted,"01",changed)
        self.assertEqual(src["global_direct"],nxt["global_direct"])
        self.assertEqual(src["venue_direct"],nxt["venue_direct"])
        # Train roster features for a unique player are separate from venue.
        self.assertNotEqual(src["venue_plus_athlete"],nxt["venue_plus_athlete"])
        self.assertNotEqual(src["global_plus_athlete"],nxt["global_plus_athlete"])


if __name__=="__main__":
    unittest.main()
