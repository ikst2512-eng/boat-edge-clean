"""Offline safety tests for original-K wind missingness sensitivity; no network."""
import unittest

from scripts.research_official_k_wind_missingness_sensitivity import (
    _rate, band_of, observation, summarize,
)


def race(wind=3, one_status="01", winner=1, unsettled=False):
    ranks = ["01", "02", "03", "04", "05", "06"]
    rows = [{"boat": i, "course": i, "status": ranks[i-1]} for i in range(1, 7)]
    if winner == 2:
        rows[0]["status"], rows[1]["status"] = "02", "01"
    if one_status == "F":
        rows[0]["status"] = "F"
    return {"venue": "03", "entries": rows, "wind_m": wind, "unsettled": unsettled}


class OfficialKWindMissingnessTests(unittest.TestCase):
    def test_display_percent_rounds_half_up_and_zero_denominator_unknown(self):
        self.assertEqual(_rate(202, 320), 63.13)
        self.assertIsNone(_rate(0, 0))

    def test_wind_band_boundaries(self):
        self.assertEqual([band_of(x) for x in (0, 2, 3, 4, 5, 10)],
                         ["0-2m", "0-2m", "3-4m", "3-4m", "5m+", "5m+"])
        with self.assertRaisesRegex(ValueError, "invalid_official_postrace_wind"):
            band_of(2.4)

    def test_missing_winning_race_creates_exact_selection_shift(self):
        rows = [
            observation("202608290301", race(winner=1), True),
            observation("202608290302", race(winner=2), False),
            observation("202608290303", race(winner=1), False),
            observation("202608290304", race(winner=2), False),
        ]
        report = summarize(rows, {"202608290301"})
        x = report["national"]
        self.assertEqual((x["official_K_C1_wins"], x["official_K_C1_eligible_n"]), (2, 4))
        self.assertEqual((x["same_primary_after_omissions_C1_wins"],
                          x["same_primary_after_omissions_C1_eligible_n"]), (1, 3))
        self.assertEqual(x["full_minus_without_missing_percentage_points"], 16.67)
        self.assertEqual(x["missing_races_20260829"], 1)
        self.assertTrue(x["postrace_only_not_T12"])

    def test_missing_F_does_not_increase_denominator(self):
        f = observation("202608290301", race(one_status="F", winner=2), True)
        a = observation("202608290302", race(winner=1), False)
        out = summarize([f, a], {f["code"]})["national"]
        self.assertEqual(out["primary_only_missing_races"], 1)
        self.assertEqual(out["official_K_C1_eligible_n"], 1)
        self.assertEqual(out["same_primary_after_omissions_C1_eligible_n"], 1)
        self.assertEqual(out["full_minus_without_missing_percentage_points"], 0)

    def test_no_winner_without_unsettled_rejected(self):
        x = race()
        x["entries"][0]["status"] = "F"
        with self.assertRaisesRegex(ValueError, "winner_invalid"):
            observation("202608290301", x, True)
        x["entries"][0]["status"] = "02"
        x["entries"][1]["status"] = "F"
        x["entries"][2]["status"] = "F"
        x["entries"][3]["status"] = "F"
        x["entries"][4]["status"] = "F"
        x["entries"][5]["status"] = "F"
        with self.assertRaisesRegex(ValueError, "winner_invalid"):
            observation("202608290301", x, True)

    def test_missing_course_not_treated_as_false(self):
        x = race()
        x["entries"][0]["course"] = None
        with self.assertRaisesRegex(ValueError, "course1_not_unique"):
            observation("202608290301", x, True)

    def test_omission_flag_mismatch_denied(self):
        x = observation("202608290301", race(), True)
        with self.assertRaisesRegex(ValueError, "flag_conflict"):
            summarize([x], set())
        with self.assertRaisesRegex(ValueError, "missing_cohort_not_in_official"):
            summarize([], {"202608290301"})

    def test_duplicate_primary_codes_denied(self):
        x = observation("202608290301", race(), False)
        with self.assertRaisesRegex(ValueError, "duplicate_official_race_code"):
            summarize([x, x], set())


if __name__ == "__main__":
    unittest.main()
