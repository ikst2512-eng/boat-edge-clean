import csv
import tempfile
import unittest
from pathlib import Path

from venue_environment_observational import (
    analyze_rows, analyze_csv, parse_result, wind_band, wilson_95,
)


def row(code="202611050101", winner=1, courses=(1, 2, 3, 4, 5, 6),
        wind="3", direction="北", method="逃げ"):
    data = {"レースコード": code, "1着_艇番": str(winner),
            "決まり手": method, "風速(m)": wind, "風向": direction}
    data.update({f"{i}コース_艇番": str(boat)
                 for i, boat in enumerate(courses, 1)})
    return data


class VenueWindResearchTests(unittest.TestCase):
    def test_wind_bands(self):
        self.assertEqual(
            [wind_band(n) for n in (0, 2, 3, 4, 5, 7)],
            ["0-2m", "0-2m", "3-4m", "3-4m", "5m+", "5m+"],
        )

    def test_actual_course_differs_from_boat_number(self):
        record = parse_result(row(winner=2, courses=(2, 1, 3, 4, 5, 6)))
        self.assertEqual(record["winner_course"], 1)
        self.assertEqual(record["winner_boat"], 2)

    def test_real_result_file_method_spacings(self):
        for method, expected in (("逃　げ", "逃げ"), ("差　し", "差し"),
                                 ("抜　き", "抜き"), ("まくり差し", "まくり差し")):
            with self.subTest(method=method):
                parsed = parse_result(row(method=method, wind="2.0", direction="3"))
                self.assertEqual(parsed["method"], expected)

    def test_missing_weather_not_zero(self):
        out = analyze_rows(
            [row(wind=""), row(code="202611050102", wind="0", direction="")],
            min_n=1,
        )
        self.assertEqual(out["accepted_unique_races"], 1)
        self.assertEqual(out["excluded"]["wind_missing_or_invalid"], 1)
        self.assertEqual(out["venue_wind_band"]["01"]["0-2m"]["n"], 1)

    def test_reject_noninteger_wind(self):
        out = analyze_rows([row(wind="2.5")], min_n=1)
        self.assertEqual(out["accepted_unique_races"], 0)
        self.assertEqual(out["excluded"]["wind_noninteger_out_of_band_definition"], 1)

    def test_duplicate_codes_discard_all_instances(self):
        out = analyze_rows(
            [row(), row(winner=2),
             row(code="202611050102", wind="2")], min_n=1
        )
        self.assertEqual(out["accepted_unique_races"], 1)
        self.assertEqual(out["excluded"]["duplicate_race_codes_removed_all"], 1)

    def test_missing_sample_sizes_do_not_make_up_deltas(self):
        out = analyze_rows(
            [row(wind="1"), row(code="202611050102", wind="5")],
            min_n=20,
        )
        strong = out["venue_wind_band"]["01"]["5m+"]
        self.assertIsNone(strong["vs_0_2m_course1_win_delta_pt"])
        self.assertFalse(strong["sufficient_n"])

    def test_course_and_method_independent(self):
        out = analyze_rows(
            [row(), row(code="202611050102", winner=2, method="差し")],
            min_n=1,
        )
        summary = out["venue_wind_band"]["01"]["3-4m"]
        self.assertEqual(summary["winner_course1_pct"], 50)
        self.assertEqual(summary["winning_method_pct"]["差し"], 50)
        self.assertEqual(sum(summary["winner_course_pct"].values()), 100)

    def test_fail_closed_incomplete_result(self):
        bad = [
            row(courses=(1, 1, 3, 4, 5, 6)),
            row(code="202611050102", wind="nan"),
            row(code="202611050103", method=""),
            row(code="202611050104", wind="3", direction=""),
        ]
        out = analyze_rows(bad, min_n=1)
        self.assertEqual(out["accepted_unique_races"], 0)
        self.assertEqual(len(out["excluded"]), 4)

    def test_sample_interval(self):
        lo, hi = wilson_95(5, 10)
        self.assertLess(lo, 50)
        self.assertGreater(hi, 50)
        self.assertIsNone(wilson_95(0, 0))

    def test_csv_schema_gate(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.csv"
            path.write_text("レースコード,風速(m)\n202611050101,3\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "result_schema_missing_columns"):
                analyze_csv(path)

    def test_no_forecast_approval(self):
        out = analyze_rows([row()], min_n=1)
        self.assertFalse(out["model_training_authorized"])
        self.assertFalse(out["formal_prediction_evidence"])
        self.assertTrue(out["weather_is_post_race"])


if __name__ == "__main__":
    unittest.main()
