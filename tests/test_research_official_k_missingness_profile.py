"""Offline postrace omission tests: race grain, winner, weather and no T-12 admission."""
import unittest

from scripts.research_official_k_missingness_profile import profile_races


def race(code="202608290101", wind=3, win_course=1):
    entries = [{"boat": i, "course": i, "status": "01" if i == win_course else f"{(i + 1 if i < win_course else i):02d}"}
               for i in range(1, 7)]
    return {"race_code": code, "entries": entries, "wind_m": wind,
            "unsettled": False}


class OfficialKMissingnessProfileTests(unittest.TestCase):
    def test_three_bands_and_first_course_win(self):
        rows = [race("202608290101", 2, 1),
                race("202608290102", 3, 2),
                race("202608290103", 5, 3)]
        profile = profile_races(rows)
        self.assertEqual(profile["missing_races"], 3)
        self.assertEqual(profile["by_postrace_wind_band"],
                         {"0-2m": 1, "3-4m": 1, "5m+": 1})
        self.assertEqual(profile["actual_first_course_result_counts"],
                         {"1C": 1, "non1C": 2, "none": 0})

    def test_duplicate_race_code_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate_or_out_of_period"):
            profile_races([race(), race()])

    def test_missing_first_course_rejected(self):
        row = race()
        row["entries"][0]["course"] = None
        with self.assertRaisesRegex(ValueError, "actual_first_course_missing"):
            profile_races([row])

    def test_unknown_winner_is_not_a_loss(self):
        row = race()
        for e in row["entries"]:
            e["status"] = "F"
        with self.assertRaisesRegex(ValueError, "no_winner_without_primary_unsettled"):
            profile_races([row])
        row["unsettled"] = True
        profile = profile_races([row])
        self.assertEqual(profile["actual_first_course_result_counts"]["none"], 1)

    def test_missing_or_duplicate_boats_rejected(self):
        row = race()
        row["entries"][5]["boat"] = 1
        with self.assertRaisesRegex(ValueError, "missing_or_duplicate_boat"):
            profile_races([row])

    def test_bad_wind_rejected(self):
        row = race(wind=-1)
        with self.assertRaisesRegex(ValueError, "invalid_primary_postrace_wind"):
            profile_races([row])


if __name__ == "__main__":
    unittest.main()
