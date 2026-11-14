"""Guard against postrace feature leakage, lost mass and false test coverage."""
import copy
from datetime import date, timedelta
import math
import unittest
from scenario_athlete_tail_world_holdout import (
    TICKETS, ALTERNATIVES, fit_training, predict_120, evaluate,
    select_from_september,
)

IDS=tuple(str(4101+i) for i in range(6))
ALT=tuple(str(5101+i) for i in range(6))


def race(day,head=1,second=4,third=5,method="逃げ",roster=IDS):
    order=(head,second,third)+tuple(b for b in range(1,7)
                                     if b not in (head,second,third))
    assert len(set(order))==6
    return {
        "day":day, "venue":"12",
        "historical_boat_to_registration":roster,
        "historical_boat_finish_6":order,
        "actual_course_finish":order,
        "method":method,
        "group":"one_escape" if method=="逃げ" else "three_makuri",
        "no_causal_attack_observed":True,
        "roster_was_extracted_from_postrace_K_not_a_predeadline_receipt":True,
    }


def august():
    return ([race("20260801") for _ in range(30)]
            + [race("20260802",3,5,4,"まくり") for _ in range(12)]
            + [race("20260803",4,5,1,"まくり差し",ALT) for _ in range(9)]
            + [race("20260804",2,1,3,"差し") for _ in range(10)])


def month(month):
    first=date(2026,month,1)
    return [race((first+timedelta(days=i)).strftime("%Y%m%d"),
                 *((1,4,5,"逃げ",IDS) if i%3==0
                   else (3,5,4,"まくり",IDS) if i%3==1
                   else (4,5,2,"まくり差し",ALT)))
            for i in range(30 if month==9 else 31)]


class FullTailTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fit=fit_training(august(),(8,))

    def test_all_120_boat_triples_and_head_unchanged(self):
        p=predict_120(self.fit,IDS)
        self.assertFalse(p["target_method_consumed"])
        self.assertFalse(p["target_actual_course_consumed"])
        for label,board in p["boards"].items():
            self.assertEqual(len(board),120)
            self.assertAlmostEqual(sum(board.values()),1,places=10)
            self.assertGreater(min(board.values()),0)
        for h in range(1,7):
            baseline=sum(p["boards"]["head_only"][t]
                         for t in TICKETS if t[0]==h)
            for name in ALTERNATIVES:
                self.assertAlmostEqual(sum(p["boards"][name][t]
                    for t in TICKETS if t[0]==h),baseline,places=10)

    def test_each_tail_candidate_changes_some_conditional_pairs(self):
        boards=predict_120(self.fit,IDS)["boards"]
        for name in ALTERNATIVES[1:]:
            self.assertTrue(any(abs(boards[name][t]-boards["head_only"][t])>1e-12
                                for t in TICKETS),name)

    def test_prediction_receives_roster_only_never_target(self):
        a=race("20261001",3,4,5,"まくり")
        b=race("20261001",1,2,3,"逃げ")
        self.assertEqual(predict_120(self.fit,a["historical_boat_to_registration"]),
                         predict_120(self.fit,b["historical_boat_to_registration"]))
        for key in ("actual_course","winning_method","outcome"):
            with self.assertRaises(TypeError):
                predict_120(self.fit,IDS,**{key:3})

    def test_training_october_or_september_contamination_rejected(self):
        for bad in ("20260901","20261001"):
            with self.assertRaisesRegex(ValueError,"period_leakage"):
                fit_training(august()+[race(bad)],(8,))
        with self.assertRaisesRegex(ValueError,"only_aug"):
            fit_training(august(),(8,9,10))

    def test_methods_change_world_but_not_old_head(self):
        f=fit_training(august(),(8,))
        changed=august()
        changed[0]["method"]="まくり差し"
        g=fit_training(changed,(8,))
        a,b=predict_120(f,IDS)["boards"],predict_120(g,IDS)["boards"]
        self.assertEqual(a["head_only"],b["head_only"])
        self.assertNotEqual(a["head_latent_style"],b["head_latent_style"])

    def test_september_pilot_october_evaluation_and_guard(self):
        pil=evaluate(self.fit,month(9),9)
        self.assertEqual(pil["n"],30)
        self.assertEqual(pil["distinct_days"],30)
        select=select_from_september(pil)
        self.assertFalse(select["chosen_from_october"])
        self.assertFalse(select["formal_preregistration_before_historical_October"])
        f=fit_training(august()+month(9),(8,9))
        oct_=evaluate(f,month(10),10,strata=True)
        self.assertEqual(oct_["n"],31)
        self.assertEqual(sum(m["head_only"]["n"] for m in
                         oct_["winner_method_postrace_diagnostic_only"].values()),31)
        self.assertFalse(oct_["outcomes_consumed_before_forecast"])
        self.assertEqual(oct_,evaluate(f,month(10),10,strata=True))
        for name in ALTERNATIVES[1:]:
            for k in (1,3,5,10):
                self.assertEqual(sum(oct_["paired_vs_head_only"][name][
                    "topk_gained_lost"][f"top{k}"].values()),31)

    def test_invalid_holdout_period_roster_and_finish_rejected(self):
        with self.assertRaisesRegex(ValueError,"holdout_outcome_period"):
            evaluate(self.fit,month(10),9)
        with self.assertRaisesRegex(ValueError,"registrations_required"):
            predict_120(self.fit,IDS[:-1]+(IDS[0],))
        with self.assertRaisesRegex(ValueError,"registrations_required"):
            predict_120(self.fit,list(IDS))
        with self.assertRaisesRegex(ValueError,"historical_six_boat_finish"):
            a=august()
            a[0]["historical_boat_finish_6"]=(1,1,3,4,5,6)
            fit_training(a,(8,))


if __name__=="__main__":
    unittest.main()
