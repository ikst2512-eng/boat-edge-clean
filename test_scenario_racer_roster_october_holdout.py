"""Fail-closed athlete prior: only Aug/Sep rider IDs and boat draw before October."""
import copy
import math
import unittest

from scenario_racer_roster_october_holdout import (
    fit_aug_sep, predict_from_boat_roster, score_october_holdout,
    STUDY, TICKETS,
)
from scenario_official_K_attack_benefit_holdout import _record_with_historical_roster

IDS = tuple(str(x) for x in range(4101, 4107))
IDS_NEW = tuple(str(x) for x in range(5101, 5107))


def history(day="20260801", head=1, second=2, third=3, roster=IDS):
    ordered = (head, second, third) + tuple(
        b for b in range(1, 7) if b not in (head, second, third))
    return {
        "day": day, "venue": "12",
        "no_causal_attack_observed": True,
        "roster_was_extracted_from_postrace_K_not_a_predeadline_receipt": True,
        "historical_boat_to_registration": tuple(roster),
        "historical_boat_finish_6": ordered,
        "actual_course_finish": ordered,
        "group": "one_escape",
    }


def train():
    return (
        [history("20260801", 1, 2, 3) for _ in range(10)] +
        [history("20260808", 2, 1, 3) for _ in range(4)] +
        [history("20260908", 3, 1, 5, roster=IDS_NEW) for _ in range(6)]
    )


class HistoricalRacerRosterHoldout(unittest.TestCase):
    def test_posterior_head_only_conditional_tail_preserved(self):
        fit = fit_aug_sep(train())
        p = predict_from_boat_roster(fit, IDS)
        self.assertEqual(len(TICKETS), 120)
        for board in (p["global_boat_baseline"], p["racer_prior_head_only"]):
            self.assertEqual(len(board), 120)
            self.assertAlmostEqual(sum(board.values()), 1, places=10)
            self.assertGreater(min(board.values()), 0)
        self.assertEqual(p["input_fields"], ("boat_number", "registration_id"))
        self.assertFalse(p["current_race_outcome_used"])
        self.assertFalse(p["current_race_actual_course_used"])
        # Candidate only alters first-place mass, NOT P(second,third|head).
        a, b = p["global_boat_baseline"], p["racer_prior_head_only"]
        for h in range(1, 7):
            base_mass = sum(a[t] for t in TICKETS if t[0] == h)
            alt_mass = sum(b[t] for t in TICKETS if t[0] == h)
            for t in TICKETS:
                if t[0] == h:
                    self.assertAlmostEqual(a[t] / base_mass, b[t] / alt_mass, places=11)

    def test_never_accept_october_in_training(self):
        with self.assertRaisesRegex(ValueError, "october_leak"):
            fit_aug_sep(train() + [history("20261001")])

    def test_new_racers_are_neutral_not_zero_wins(self):
        fit = fit_aug_sep(train())
        a = predict_from_boat_roster(fit, tuple(str(x) for x in range(6101, 6107)))
        self.assertEqual(a["racer_coverage"], 0)
        self.assertEqual(a["global_boat_baseline"], a["racer_prior_head_only"])
        self.assertEqual(a["global_head"], a["racer_head"])

    def test_target_course_or_result_is_not_a_predictor_argument(self):
        fit = fit_aug_sep(train())
        original = history("20261001")
        new = history("20261001", head=5, second=3, third=1)
        new["actual_course_finish"] = tuple(reversed(new["actual_course_finish"]))
        self.assertEqual(predict_from_boat_roster(
            fit, original["historical_boat_to_registration"]),
            predict_from_boat_roster(
            fit, new["historical_boat_to_registration"]))
        with self.assertRaises(TypeError):
            predict_from_boat_roster(fit, IDS, actual_course=3)
        with self.assertRaises(TypeError):
            predict_from_boat_roster(fit, IDS, winning_method="まくり")

    def test_duplicate_athlete_and_wrong_roster_type_are_rejected(self):
        f = fit_aug_sep(train())
        bad = IDS[:-1] + (IDS[0],)
        with self.assertRaisesRegex(ValueError, "six_registrations"):
            predict_from_boat_roster(f, bad)
        with self.assertRaisesRegex(ValueError, "six_registrations"):
            predict_from_boat_roster(f, list(IDS))

    def test_retrospective_holdout_scores_paired_same_races(self):
        f = fit_aug_sep(train())
        holdout = [history("20261001"),
                   history("20261002", 2, 1, 3),
                   history("20261003", 3, 2, 5, roster=IDS_NEW)]
        a = score_october_holdout(f, holdout)
        b = score_october_holdout(f, holdout)
        self.assertEqual(a, b)
        self.assertEqual(a["study_id"], STUDY)
        self.assertEqual(a["train_n"], len(train()))
        self.assertEqual(a["october_holdout_n"], len(holdout))
        for model in a["models"].values():
            self.assertEqual(model["n"], 3)
            self.assertGreater(model["logloss"], 0)
            self.assertTrue(0 < model["head_logloss"] < 10)
        for k, tally in a["topk_gained_lost"].items():
            self.assertEqual(sum(tally.values()), 3)
        self.assertFalse(a["adoption_guard"]["all_pass"])
        self.assertFalse(a["adoption_guard"]["model_switch_allowed"])
        self.assertFalse(a["promotion_allowed"])
        self.assertTrue(a["source_is_historical_postrace_K_not_independent_T12"])

    def test_wrong_october_period_fails(self):
        f = fit_aug_sep(train())
        with self.assertRaisesRegex(ValueError, "holdout_date"):
            score_october_holdout(f, [history("20260901")])
        with self.assertRaisesRegex(ValueError, "size_mismatch"):
            score_october_holdout(f, [history("20261002")], expected_oct_n=4382)

    def test_actual_method_is_training_diagnostic_only(self):
        x = train()
        f1 = fit_aug_sep(x)
        changed = copy.deepcopy(x)
        changed[0]["group"] = "four_makuri"
        f2 = fit_aug_sep(changed)
        p1 = predict_from_boat_roster(f1, IDS)
        p2 = predict_from_boat_roster(f2, IDS)
        self.assertEqual(p1, p2)
        self.assertTrue(all("style_wins_training_only" in v for v in f1["athlete"].values()))

    def test_historical_registration_from_original_k_shape(self):
        entries = []
        for boat, reg in enumerate(IDS, 1):
            entries.append({"boat":boat,"course":boat,
                            "status":f"{boat:02d}",
                            "athlete_registration":reg})
        raw = {"entries": entries, "unsettled": False, "method":"逃げ"}
        r = _record_with_historical_roster(raw)
        self.assertEqual(r["historical_boat_to_registration"], IDS)
        self.assertEqual(r["historical_boat_finish_6"], (1,2,3,4,5,6))
        self.assertTrue(r["roster_was_extracted_from_postrace_K_not_a_predeadline_receipt"])
        entries[0]["athlete_registration"]="--"
        with self.assertRaisesRegex(ValueError, "registration_invalid"):
            _record_with_historical_roster(raw)


if __name__ == "__main__":
    unittest.main()
