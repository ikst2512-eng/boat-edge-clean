"""Negative and descriptive tests for immutable ORIGINAL full-list calibration."""
import copy
import json
import math
import shutil
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from four_mode_original_coverage_calibration_audit import (
    _estimated_coverage, _new_stats, _accumulate, _summarize, audit,
)
from four_mode_nov05_08_daily_reference_audit import ROOT, DAYS, MODES

CODE = "202611080101"
CLOCK = datetime.fromisoformat("2026-11-08T20:53:00+09:00")
CSV_HEADER = "レースコード,取得日時,1着_艇番,2着_艇番,3着_艇番\n"


class OriginalCoverageCalibrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for directory in ("four_mode_forecasts", "confirmed_results"):
            (self.root / directory).mkdir()
        shutil.copyfile(ROOT / "four_mode_forecasts" / (CODE + ".json"),
                        self.root / "four_mode_forecasts" / (CODE + ".json"))
        shutil.copyfile(ROOT / "confirmed_results" / (CODE + ".json"),
                        self.root / "confirmed_results" / (CODE + ".json"))
        self.forecast = json.loads(
            (self.root / "four_mode_forecasts" / (CODE + ".json")).read_bytes())
        self.saved = json.loads(
            (self.root / "confirmed_results" / (CODE + ".json")).read_bytes())

    def test_displayed_estimate_is_original_raw_field_not_ticket_p_sum(self):
        for mode in MODES:
            expected = self.forecast["modes"][mode]["estimated_coverage_pct"] / 100
            p, combos = _estimated_coverage(self.forecast, mode)
            self.assertAlmostEqual(p, expected)
            self.assertEqual(len(combos), {"narrow": 5, "hit": 10,
                                          "balance": 16, "hole": 22}[mode])

    def test_missing_estimated_coverage_is_not_zero(self):
        bad = copy.deepcopy(self.forecast)
        del bad["modes"]["hit"]["estimated_coverage_pct"]
        with self.assertRaisesRegex(ValueError, "missing_or_invalid_original_estimated_coverage"):
            _estimated_coverage(bad, "hit")

    def test_nonfinite_bool_or_out_of_bounds_estimate_rejected(self):
        for value in (True, -1, 100.0001, float("nan"), float("inf"), "50"):
            bad = copy.deepcopy(self.forecast)
            bad["modes"]["balance"]["estimated_coverage_pct"] = value
            with self.subTest(value=value), self.assertRaisesRegex(
                    ValueError, "missing_or_invalid_original_estimated_coverage"):
                _estimated_coverage(bad, "balance")

    def test_mutated_budget_and_duplicate_ticket_rejected(self):
        bad = copy.deepcopy(self.forecast)
        bad["modes"]["hole"]["tickets"].pop()
        with self.assertRaisesRegex(ValueError, "original_ticket_budget_mismatch"):
            _estimated_coverage(bad, "hole")
        bad = copy.deepcopy(self.forecast)
        bad["modes"]["hole"]["tickets"][-1]["combo"] = bad["modes"]["hole"]["tickets"][0]["combo"]
        with self.assertRaisesRegex(ValueError, "duplicate_original_ticket"):
            _estimated_coverage(bad, "hole")

    def test_full_coverage_vs_top10_and_signed_gap_math(self):
        data = _new_stats()
        _accumulate(data, .8, True, "persisted")
        _accumulate(data, .3, False, "public_unarchived")
        report = _summarize(data)
        self.assertEqual(report["races"], 2)
        self.assertEqual(report["estimated_full_list_hit_rate_pct"], 55.0)
        self.assertEqual(report["observed_full_list_hit_rate_pct"], 50.0)
        self.assertEqual(report["observed_minus_estimated_percentage_points"], -5.0)
        self.assertEqual(report["observed_hit_count"], 1)
        self.assertAlmostEqual(report["mean_squared_error_brier_descriptive"], .065)
        self.assertEqual(report["persisted_result_count"], 1)
        self.assertEqual(report["public_only_result_count"], 1)
        self.assertEqual(report["estimated_full_list_min_pct"], 30.0)
        self.assertEqual(report["estimated_full_list_max_pct"], 80.0)
        self.assertEqual(report["estimated_full_list_population_stddev_pp"], 25.0)
        self.assertEqual(report["distinct_original_estimated_pct_values"], 2)

    def test_empty_spread_uses_unknown_not_zero(self):
        row = _summarize(_new_stats())
        self.assertIsNone(row["estimated_full_list_min_pct"])
        self.assertIsNone(row["estimated_full_list_max_pct"])
        self.assertIsNone(row["estimated_full_list_population_stddev_pp"])
        self.assertEqual(row["distinct_original_estimated_pct_values"], 0)

    def test_identical_estimates_cannot_fake_race_discrimination(self):
        stats = _new_stats()
        _accumulate(stats, 0.4, True, "persisted")
        _accumulate(stats, 0.4, False, "persisted")
        _accumulate(stats, 0.4, False, "public_unarchived")
        row = _summarize(stats)
        self.assertEqual(row["estimated_full_list_min_pct"], 40.0)
        self.assertEqual(row["estimated_full_list_max_pct"], 40.0)
        self.assertEqual(row["estimated_full_list_population_stddev_pp"], 0.0)
        self.assertEqual(row["distinct_original_estimated_pct_values"], 1)
        self.assertEqual(row["observed_full_list_hit_rate_pct"], 33.33)

    def test_bad_accumulated_probability_never_silently_admitted(self):
        for value in (float("nan"), -0.001, 1.001, True):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "untrusted_estimated_probability"):
                    _accumulate(_new_stats(), value, False, "persisted")

    def _raws(self, order=(1, 2, 5), source_stamp=None):
        ts = source_stamp or self.saved["confirmed_at_jst"]
        one = (CSV_HEADER + f"{CODE},{ts},{order[0]},{order[1]},{order[2]}\n").encode()
        return {day: one if day == "20261108" else CSV_HEADER.encode() for day in DAYS}

    @staticmethod
    def _fake_external_gate(*, evaluated=1, missing=0):
        return {"frozen_original_result_reference": {
            "forecast_files": 1, "evaluated": evaluated, "pending_results": missing
        }, "totals": {
            "saved_result_rows_disagree_or_not_present": 0,
            "saved_result_rows_matched_current_csv": evaluated
        }}

    @staticmethod
    def _fake_official_gate(non_scored=0, unresolved=0):
        return {"reviewed_non_scored_races": [],
                "non_scored_total": non_scored,
                "remaining_unresolved_result_races": unresolved}

    def run_minimal(self, raws, *, evaluated=1, missing=0, non_scored=0, unresolved=0):
        with patch("four_mode_original_coverage_calibration_audit.evaluate",
                   return_value=self._fake_external_gate(evaluated=evaluated,
                                                         missing=missing)), \
             patch("four_mode_original_coverage_calibration_audit.annotate_official_non_scored",
                   return_value=self._fake_official_gate(
                       non_scored=non_scored, unresolved=unresolved)):
            return audit(self.root, raws, {}, observed_at=CLOCK)

    def test_saved_original_score_is_one_not_a_new_candidate(self):
        report = self.run_minimal(self._raws())
        self.assertEqual(report["postrace_scoreable"], 1)
        self.assertEqual(report["persisted_results"], 1)
        self.assertEqual(report["public_only_postrace_results"], 0)
        self.assertEqual(report["mode"]["narrow"]["observed_hit_count"], 1)
        self.assertFalse(report["formal"])
        self.assertFalse(report["predictive_calibration_proven"])
        self.assertFalse(report["model_promotion_allowed"])
        self.assertEqual(report["prospective_candidate_pairs"], 0)

    def test_saved_result_order_mismatch_rejected(self):
        with self.assertRaisesRegex(ValueError, "saved_source_result_mismatch"):
            self.run_minimal(self._raws(order=(2, 1, 5)))

    def test_missing_uncancelled_outcome_rejected(self):
        with self.assertRaisesRegex(ValueError, "missing_nonexcluded_published_trifecta"):
            self.run_minimal({day: CSV_HEADER.encode() for day in DAYS})

    def test_future_source_not_accepted_as_postrace_observation(self):
        with self.assertRaisesRegex(ValueError, "missing_nonexcluded_published_trifecta"):
            self.run_minimal(self._raws(source_stamp="2026-11-08T21:00:00+09:00"))

    def test_public_only_result_is_separate_from_archived(self):
        (self.root / "confirmed_results" / (CODE + ".json")).unlink()
        report = self.run_minimal(self._raws(), evaluated=0, missing=1, unresolved=1)
        self.assertEqual(report["persisted_results"], 0)
        self.assertEqual(report["public_only_postrace_results"], 1)
        self.assertEqual(report["mode"]["hit"]["public_only_result_count"], 1)
        self.assertFalse(report["formal"])

    def test_forged_incomplete_official_roster_rejected(self):
        with self.assertRaisesRegex(ValueError, "non_scoreable_duplicate"):
            self.run_minimal(self._raws(), non_scored=1, unresolved=0)


if __name__ == "__main__":
    unittest.main()
