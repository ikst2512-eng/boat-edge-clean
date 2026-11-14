"""No hindsight model: retrospective official K finish-method associations only."""
import unittest

from scenario_official_K_attack_benefit_holdout import (
    _record, _wilson, summarize, GROUPS,
)


def race(first_course=3, method="まくり", second=4, third=5, courses=None):
    rest = [c for c in range(1, 7) if c not in (first_course, second, third)]
    positions = courses if courses is not None else [first_course, second, third, *rest]
    return {
        "unsettled": False, "method": method,
        "entries": [
            {"boat": i + 1, "course": course, "status": f"{pos+1:02d}"}
            for i, (pos, course) in enumerate((p, c) for p,c in enumerate(positions))
        ],
    }


class HistoricalOutcomeRules(unittest.TestCase):
    def test_three_makuri_companions(self):
        record = _record(race())
        self.assertEqual(record["group"], "three_makuri")
        self.assertEqual(record["actual_course_finish"][:3], (3, 4, 5))
        s = summarize([record])["three_makuri"]
        self.assertEqual(s["races"], 1)
        self.assertEqual(s["rates"]["course4_second"]["count"], 1)
        self.assertEqual(s["rates"]["course5_third"]["count"], 1)
        self.assertEqual(s["rates"]["course5_second"]["count"], 0)
        self.assertEqual(s["rates"]["four_and_five_both_top3"]["count"], 1)

    def test_method_changes_label_not_finishing_order(self):
        a = _record(race(method="まくり"))
        b = _record(race(method="まくり差し"))
        self.assertNotEqual(a["group"], b["group"])
        self.assertEqual(a["actual_course_finish"], b["actual_course_finish"])

    def test_actual_course_not_boat_number(self):
        # Boat1 comes from course3, boat3 from course1: winner method still C3.
        r = race()
        by_course = {e["course"]: e["status"] for e in r["entries"]}
        new_courses = [3, 2, 1, 4, 5, 6]
        for e, actual_course in zip(r["entries"], new_courses):
            e["course"] = actual_course
            e["status"] = by_course[actual_course]
        self.assertEqual(_record(r)["group"], "three_makuri")

    def test_omit_incomplete_finishers_and_unsettled(self):
        x = race()
        x["entries"][-1]["status"] = "F"
        self.assertIsNone(_record(x))
        y = race()
        y["unsettled"] = True
        self.assertIsNone(_record(y))

    def test_wrong_escape_from_outer_course_rejected(self):
        self.assertIsNone(_record(race(first_course=3, method="逃げ")))
        self.assertEqual(_record(race(first_course=1, method="逃げ"))["group"], "one_escape")

    def test_zero_denominator_not_100_percent(self):
        z = summarize([])["three_makuri"]
        self.assertEqual(z["races"], 0)
        self.assertIsNone(z["rates"]["course5_second"]["percent"])
        self.assertIsNone(z["rates"]["course5_second"]["wilson_95_pct"])

    def test_finished_association_not_prediction(self):
        x = _record(race())
        self.assertTrue(x["no_causal_attack_observed"])
        self.assertNotIn("probability", x)
        with self.assertRaisesRegex(ValueError, "retrospective"):
            summarize([dict(x, no_causal_attack_observed=False)])

    def test_wilson_interval_boundaries(self):
        self.assertEqual(_wilson(0, 0)["denominator"], 0)
        self.assertTrue(0 <= _wilson(5, 10)["wilson_95_pct"][0] < 50)
        self.assertTrue(50 < _wilson(5, 10)["wilson_95_pct"][1] <= 100)

    def test_group_values_are_registered(self):
        self.assertEqual(len(GROUPS), 10)
        self.assertEqual(_record(race(first_course=4, second=3, method="まくり"))["group"], "four_makuri")


if __name__ == "__main__":
    unittest.main()
