"""Retrospective 8/9 -> 10 evaluation must never read Oct label to forecast."""
import copy
import math
import unittest

from scenario_course_scenario_october_holdout import (
    STUDY, GROUPS, TICKETS, fit_aug_sep, predict_at_venue,
    score_october_holdout, _validate_record,
)


def rec(day, venue="12", first=3, second=4, third=5, method="まくり"):
    places = [first, second, third]
    if len(set(places)) != 3:
        raise ValueError("bad_test_fixture_duplicate_course")
    places.extend(i for i in range(1, 7) if i not in places)
    group = ("three_makuri" if first == 3 and method == "まくり"
             else "three_makuri_sashi" if first == 3 and method == "まくり差し"
             else "four_makuri" if first == 4 and method == "まくり"
             else "one_escape" if first == 1 and method == "逃げ"
             else "all_other")
    return {"day": day, "venue": venue, "group": group,
            "method": method,
            "actual_course_finish": tuple(places),
            "no_causal_attack_observed": True}


def training():
    return ([rec("20260801", second=4, third=5) for _ in range(12)]
            + [rec("20260802", second=1, third=4) for _ in range(5)]
            + [rec("20260903", venue="01", first=1, second=2, third=3,
                   method="逃げ") for _ in range(8)]
            + [rec("20260910", venue="12", first=3, second=1, third=5,
                   method="まくり差し") for _ in range(7)])


class VenueScenarioHoldout(unittest.TestCase):
    def test_result_blind_120_distribution_and_mass(self):
        fitted = fit_aug_sep(training())
        prediction = predict_at_venue(fitted, "12")
        self.assertEqual(len(TICKETS), 120)
        for model in ("baseline_global", "venue_scenario"):
            self.assertEqual(len(prediction[model]), 120)
            self.assertAlmostEqual(sum(prediction[model].values()), 1, places=11)
            self.assertGreater(min(prediction[model].values()), 0)
        self.assertFalse(prediction["result_or_target_method_consumed"])
        self.assertFalse(prediction["final_entry_consumed"])
        self.assertFalse(fitted["contains_october_labels"])

    def test_target_winning_method_and_finish_never_used_by_predict(self):
        fit = fit_aug_sep(training())
        original = rec("20261002", first=3, second=4, third=5,
                       method="まくり")
        altered = rec("20261002", first=3, second=1, third=4,
                      method="まくり差し")
        p1 = predict_at_venue(fit, original["venue"])
        p2 = predict_at_venue(fit, altered["venue"])
        self.assertEqual(p1, p2)
        self.assertNotEqual(original["group"], altered["group"])

    def test_training_period_must_exclude_all_october_labels(self):
        x = training()
        x.append(rec("20261001"))
        with self.assertRaisesRegex(ValueError, "period_leakage"):
            fit_aug_sep(x)
        x = training()
        x[0]["day"] = "20261101"
        with self.assertRaisesRegex(ValueError, "period_leakage"):
            fit_aug_sep(x)

    def test_holdout_rejects_training_period_and_bad_group(self):
        fit = fit_aug_sep(training())
        with self.assertRaisesRegex(ValueError, "period_leakage"):
            score_october_holdout(fit, [rec("20260915")])
        bad = rec("20261015")
        bad["group"] = "four_makuri"
        with self.assertRaisesRegex(ValueError, "winner_method_group"):
            score_october_holdout(fit, [bad])

    def test_holdout_is_deterministic_and_period_separate(self):
        fit = fit_aug_sep(training())
        holdout = [rec("20261001", first=3, second=4, third=5),
                   rec("20261002", first=1, second=2, third=3,
                       method="逃げ"),
                   rec("20261003", first=3, second=1, third=4,
                       method="まくり差し")]
        one = score_october_holdout(fit, holdout)
        two = score_october_holdout(fit, holdout)
        self.assertEqual(one, two)
        self.assertEqual(one["historical_holdout_oct_n"], 3)
        self.assertEqual(one["train_n"], len(training()))
        self.assertEqual(one["study_id"], STUDY)
        self.assertFalse(one["prospective_accuracy_established"])
        self.assertFalse(one["future_prediction_allowed"])
        gate = one["frozen_adoption_gate"]
        self.assertFalse(gate["all_checks_passed"])
        self.assertFalse(gate["model_switch_allowed"])
        self.assertFalse(gate["checks"]["independent_T12_first_remote_receipt"])
        self.assertFalse(gate["checks"]["300_plus_300_prospective_pass"])
        self.assertEqual(set(gate["checks"]),
            {f"top{k}_nonregression" for k in (1,3,5,10)} |
            {"paired_logloss_upper95_below_zero", "paired_brier120_nonregression",
             "known_before_deadline_actual_entry",
             "independent_T12_first_remote_receipt",
             "300_plus_300_prospective_pass",
             "preregistered_before_future_predictions"})
        for name, stats in one["baselines"].items():
            self.assertEqual(stats["n"], 3)
            self.assertTrue(0 < stats["logloss"] < 30)
            self.assertTrue(0 < stats["brier120"] < 2)
        for k in (1, 3, 5, 10):
            self.assertEqual(sum(one["head_to_head_topk"][k].values()), 3)

    def test_unknown_venue_uses_national_scenario_prior(self):
        f = fit_aug_sep(training())
        a = predict_at_venue(f, "24")
        self.assertEqual(a["scenario_weights"], f["group_prior"])
        self.assertTrue(math.isclose(sum(a["venue_scenario"].values()), 1))

    def test_duplicate_courses_rejected(self):
        x = rec("20260801")
        x["actual_course_finish"] = (3, 4, 5, 1, 2, 3)
        with self.assertRaisesRegex(ValueError, "six_actual_course_labels"):
            fit_aug_sep([x])

    def test_score_october_cohort_count_fail_closed(self):
        f = fit_aug_sep(training())
        with self.assertRaisesRegex(ValueError, "cohort_size"):
            score_october_holdout(f, [rec("20261001")],
                                   expected_oct_n=4382)

    def test_invalid_venue_and_target_result_not_on_predict_surface(self):
        f = fit_aug_sep(training())
        with self.assertRaisesRegex(ValueError, "venue_code"):
            predict_at_venue(f, {"venue": "12", "winner": 3})
        with self.assertRaisesRegex(ValueError, "venue_code"):
            predict_at_venue(f, "99")
        with self.assertRaises(TypeError):
            predict_at_venue(f, "12", method="まくり")


if __name__ == "__main__":
    unittest.main()
