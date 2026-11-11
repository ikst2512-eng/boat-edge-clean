"""Result-blind HEAD-prior shadow safety tests. No historical hit-rate use."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from clean_four_modes import rank_modes
from research_model import probabilities
from test_four_mode_all_mode_same_job_shadow import make_original
from four_mode_top1_head_prior_shadow import (
    RULE, PRIOR_POWER, BETA, choose, audit_day,
)


def strong_second_boat():
    raw = make_original()
    raw["input_national_win_rates"] = [4.5, 7.0, 4.5, 4.5, 4.5, 4.5]
    raw["modes"] = rank_modes(probabilities(raw["input_national_win_rates"]))
    return raw


class HeadPriorShadowTests(unittest.TestCase):
    def test_fixed_hypothesis_constants(self):
        self.assertEqual(PRIOR_POWER, 0.5)
        self.assertEqual(BETA, 0.4)
        self.assertEqual(RULE, "hit_head_prior_sqrt_with_original_national_beta04_v1")

    def test_default_baseline_is_not_changed_just_for_diversity(self):
        raw = make_original()
        original_bytes = json.dumps(raw, sort_keys=True)
        out = choose(raw)
        self.assertEqual(out["candidate_first_boat"], 1)
        self.assertFalse(out["hit_first_boat_changed"])
        self.assertFalse(out["hit_top10_membership_changed"])
        self.assertEqual(out["candidate"], out["original"])
        self.assertEqual(json.dumps(raw, sort_keys=True), original_bytes)
        self.assertFalse(out["formal"])
        self.assertFalse(out["model_promotion_allowed"])

    def test_stronger_other_boat_changes_head_without_forced_hole_edit(self):
        raw = strong_second_boat()
        old_json = json.dumps(raw, sort_keys=True)
        out = choose(raw)
        self.assertEqual(out["original_hit_top1"][0], "1")
        self.assertEqual(out["candidate_first_boat"], 2)
        self.assertEqual(out["candidate_hit_top1"][0], "2")
        self.assertTrue(out["hit_first_boat_changed"])
        for mode in ("narrow", "balance", "hole"):
            self.assertEqual(out["candidate"][mode], out["original"][mode])
        self.assertEqual(len(out["candidate"]["hit"]), 10)
        self.assertEqual(len(set(out["candidate"]["hit"])), 10)
        self.assertEqual(json.dumps(raw, sort_keys=True), old_json)
        self.assertEqual(out, choose(copy.deepcopy(raw)))

    def test_postrace_fields_cannot_enter_shadow(self):
        raw = strong_second_boat()
        raw["finish_order"] = [2, 1, 3]
        with self.assertRaisesRegex(ValueError, "postrace_content_in_forecast"):
            choose(raw)

    def test_forged_saved_original_rejected(self):
        raw = strong_second_boat()
        raw["modes"]["hit"]["tickets"][0]["p"] = 99.9
        with self.assertRaisesRegex(ValueError, "original_not_exactly_reproducible"):
            choose(raw)

    def test_missing_racer_rate_refused(self):
        raw = strong_second_boat()
        raw["input_national_win_rates"][3] = None
        with self.assertRaisesRegex(ValueError, "invalid_six_national_rates"):
            choose(raw)

    def test_historical_replay_reads_no_results_and_reports_head_changes(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            path = root / "four_mode_forecasts" / "202611080101.json"
            path.parent.mkdir(parents=True)
            raw = strong_second_boat()
            raw["race_code"] = "202611080101"
            path.write_text(json.dumps(raw), encoding="utf-8")
            bad_result = root / "confirmed_results" / "202611080101.json"
            bad_result.parent.mkdir(parents=True)
            bad_result.write_bytes(b"not-json-and-intentionally-invalid")
            report = audit_day(root, "20261108")
            self.assertEqual(report["original_forecasts"], 1)
            self.assertEqual(report["candidate_head_changes"], 1)
            self.assertEqual(report["candidate_top1_heads"], {"2": 1})
            self.assertTrue(report["non_hit_modes_unchanged"])
            self.assertFalse(report["results_read"])
            self.assertFalse(report["formal"])
            self.assertFalse(report["model_improvement_proven"])

    def test_future_race_not_reused_as_discovery(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError, "not_discovery_input_date"):
                audit_day(Path(d), "20261109")

    def test_empty_day_is_not_zero_change_success(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "four_mode_forecasts").mkdir()
            with self.assertRaisesRegex(ValueError, "empty_discovery_input_set"):
                audit_day(Path(d), "20261108")


if __name__ == "__main__":
    unittest.main()
