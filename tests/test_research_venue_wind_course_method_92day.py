"""Tests for strictly postrace 92-day course-method study, no live downloads."""
import unittest
from scripts.research_venue_wind_course_method_92day import (
    aggregate, expected_by_day, git_blob_sha, reconcile, BANDS
)


def row(code="202608010101", winner="2", method="差　し", wind="3",
        courses=(1, 2, 3, 4, 5, 6), wave="5", st="0.12"):
    record = {
        "レースコード": code, "1着_艇番": winner, "決まり手": method,
        "風速(m)": wind, "風向": "2", "波の高さ(cm)": wave,
        "1コース_スタートタイミング": st, "1コース_F": "",
    }
    for i, c in enumerate(courses, 1):
        record[f"{i}コース_艇番"] = str(c)
    return record


class CourseMethodStudyTests(unittest.TestCase):
    def test_blob_sha_matches_git_object_format(self):
        import hashlib
        b = b"hello\n"
        expect = hashlib.sha1(b"blob 6\0hello\n").hexdigest()
        self.assertEqual(git_blob_sha(b), expect)

    def test_manifest_all_92_days_required(self):
        with self.assertRaisesRegex(ValueError, "manifest"):
            expected_by_day({"period": "2026-08-01 to 2026-10-31",
                             "source_hashes_per_day": []})

    def test_actual_course_not_boat_id(self):
        x = aggregate([row(courses=(2, 1, 3, 4, 5, 6))], min_n=1)
        group = x["national"]["3-4m"]
        self.assertEqual(group["course1_wins"], 1)
        self.assertEqual(group["events"]["2C_差し"]["count"], 0)
        self.assertEqual(group["course_method_counts"]["1C_差し"], 1)

    def test_real_2c_sashi_cross_and_denominator(self):
        x = aggregate([row(), row(code="202608010102", winner="1",
                                  method="逃　げ", wind="3")], min_n=1)
        z = x["national"]["3-4m"]
        self.assertEqual(z["n"], 2)
        self.assertEqual(z["events"]["2C_差し"]["count"], 1)
        self.assertEqual(z["events"]["2C_差し"]["rate_of_all_races_pct"], 50.0)
        self.assertEqual(z["methods"]["差し"], 1)
        self.assertEqual(z["winning_courses"]["2"], 1)

    def test_missing_wave_and_f_st_are_not_coded_zero(self):
        bad = row(wave="", st="-0.02")
        bad["1コース_F"] = "F"
        z = aggregate([bad], min_n=1)["national"]["3-4m"]
        self.assertEqual(z["wave_missing"], 1)
        self.assertEqual(z["wave_n"], 0)
        self.assertIsNone(z["wave_mean_cm"])
        self.assertEqual(z["st1_f_n"], 1)
        self.assertEqual(z["st1_missing_or_f"], 1)
        self.assertIsNone(z["st1_mean_nonf_seconds"])

    def test_duplicate_same_code_fails_closed(self):
        rows = [row(), row(winner="3"), row(code="202608010102", winner="1")]
        x = aggregate(rows, min_n=1)
        self.assertEqual(x["record_count_input"], 3)
        self.assertEqual(x["record_count_valid"], 1)
        self.assertEqual(x["excluded"]["duplicate_race_codes_removed_all"], 1)

    def test_data_not_eligible_for_model(self):
        x = aggregate([row()], min_n=2)
        self.assertTrue(x["weather_is_postrace"])
        self.assertFalse(x["model_training_authorized"])
        self.assertFalse(x["formal_prediction_evidence"])
        self.assertFalse(x["national"]["3-4m"]["adequate_exploratory_n_100"])
        self.assertEqual(list(x["national"]), list(BANDS))

    def test_original_baseline_reconciliation_rejects_wrong_population(self):
        x = aggregate([row()], min_n=1)
        with self.assertRaisesRegex(ValueError, "input count"):
            reconcile(x, {"input_rows": 13, "eligible_unique_races": 13})


if __name__ == "__main__":
    unittest.main()
