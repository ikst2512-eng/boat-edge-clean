"""Pure offline unit tests for postrace historical C1/C2 chronology."""
from datetime import date, timedelta
import unittest
from scripts.research_official_k_c2_athlete_chronological_holdout import (
    losses_for_target, pclip, FIELDS, MODELS
)

def example():
    training=[]
    for k in range(72):
        training.append({
            "venue": "01" if k%2 else "02",
            "c1_registration": "1001" if k%3 else "1002",
            "c2_registration": "2001" if k%4 else "2002",
            "c1_escape": int(k%3==0),
            "c2_sashi": int(k%7==0),
        })
    october=[]
    for k in range(31):
        october.append({
            "day":(date(2026,10,1)+timedelta(days=k)).strftime("%Y%m%d"),
            "venue":"01" if k%2 else "02",
            "c1_registration":"1001" if k%3 else "9998",
            "c2_registration":"2001" if k%4 else "9999",
            "c1_escape":int(k%3==0),
            "c2_sashi":int(k%7==0),
        })
    return training,october

class ChronologicalC2Test(unittest.TestCase):
    def test_labels_are_frozen(self):
        self.assertEqual(FIELDS,("c1_escape","c2_sashi"))
        self.assertIn("venue_plus_c2", MODELS)

    def test_probability_clip(self):
        self.assertEqual(pclip(-1),0.005)
        self.assertEqual(pclip(2),0.995)

    def test_all_models_and_metrics_produce_stable_finite_scores(self):
        train,test=example()
        for t in FIELDS:
            r=losses_for_target(train,test,t)
            self.assertEqual(r["training_n"],72)
            self.assertEqual(r["holdout_n"],31)
            self.assertEqual(r["paired_October_day_bootstrap"]["days"],31)
            self.assertEqual(set(r["models"]),set(MODELS))
            for m in MODELS:
                self.assertTrue(0<=r["models"][m]["brier"]<=1)
                self.assertTrue(r["models"][m]["logloss"]>=0)

    def test_october_outcomes_cannot_mutate_training_rate(self):
        train,test=example()
        a=losses_for_target(train,test,"c1_escape")
        modified=[dict(x,c1_escape=1-x["c1_escape"]) for x in test]
        b=losses_for_target(train,modified,"c1_escape")
        self.assertEqual(a["training_target_rate"],b["training_target_rate"])
        self.assertNotEqual(a["models"]["venue"]["observed_rate"],b["models"]["venue"]["observed_rate"])

    def test_unseen_c2_athletes_get_zero_training_residual(self):
        train,test=example()
        a=losses_for_target(train,test,"c2_sashi")
        transformed=[dict(x,c2_registration="9999") for x in test]
        b=losses_for_target(train,transformed,"c2_sashi")
        self.assertLess(a["holdout_c2_seen_in_train"],31)
        self.assertEqual(b["holdout_c2_seen_in_train"],0)
        self.assertEqual(b["models"]["venue_plus_c2"],b["models"]["venue"])

    def test_only_31_october_day_blocks_accepted(self):
        train,test=example()
        with self.assertRaisesRegex(ValueError, "test_days_not_31"):
            losses_for_target(train,test[:-1],"c1_escape")

    def test_unknown_target_rejected(self):
        train,test=example()
        with self.assertRaisesRegex(ValueError,"unsupported_target"):
            losses_for_target(train,test,"postrace_wind_angle")

    def test_deterministic_results(self):
        train,test=example()
        a=losses_for_target(train,test,"c2_sashi")
        b=losses_for_target(train,test,"c2_sashi")
        self.assertEqual(a,b)

if __name__=="__main__":
    unittest.main()
