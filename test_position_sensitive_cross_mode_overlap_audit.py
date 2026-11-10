"""Regression tests: mode overlap is measured, never forced away."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from clean_four_modes import rank_modes
from research_model import probabilities
from four_mode_position_sensitive_shadow import shadow_modes, BASELINE_VERSION
from position_sensitive_cross_mode_overlap_audit import (
    _per_race, audit_same_race_overlap, MODES, PAIRS, BUDGETS,
)

RATES = [5.4, 7.3, 4.6, 6.5, 6.1, 4.9]


def record(code, rates):
    return {
        "race_code": code,
        "schema": "CLEAN_FOUR_MODES_PREDEADLINE_V1",
        "model_version": BASELINE_VERSION,
        "validated": False,
        "target_rates_not_proven": True,
        "generated_at_jst": "2026-11-10T12:03:00+09:00",
        "deadline_jst": "2026-11-10T16:23:00+09:00",
        "input_national_win_rates": rates,
        "modes": rank_modes(probabilities(rates)),
    }


class CrossModeOverlapTests(unittest.TestCase):
    def setUp(self):
        self.baseline = rank_modes(probabilities(RATES))
        self.shadow = shadow_modes(RATES)["modes"]

    def test_narrow_is_always_nested_in_hit_not_solved_by_conditional_tilt(self):
        row = _per_race(self.baseline, self.shadow)
        for version in ("original", "frozen_candidate"):
            self.assertTrue(row[version]["narrow_is_subset_of_hit"])
            self.assertTrue(row[version]["pairs"]["narrow__hit"]["top1_identical"])
            self.assertEqual(row[version]["pairs"]["narrow__hit"]["shared_tickets"], 5)
            self.assertEqual(row[version]["pairs"]["narrow__hit"]["overlap_fraction_of_smaller_mode"], 1)
        self.assertFalse(row["forced_diversification_applied"])

    def test_four_modes_have_real_preserved_ticket_budgets(self):
        row = _per_race(self.baseline, self.shadow)
        for label in ("original_tickets", "frozen_candidate_tickets"):
            self.assertEqual({m: len(v) for m, v in row[label].items()}, BUDGETS)
        for label in ("original", "frozen_candidate"):
            self.assertEqual(len(row[label]["pairs"]), 6)
            self.assertIn(row[label]["distinct_top1_mode_tickets"], range(1, 5))

    def test_missing_mode_rejects(self):
        m=copy.deepcopy(self.shadow)
        del m["hole"]
        with self.assertRaisesRegex(ValueError, "missing_or_extra_mode"):
            _per_race(self.baseline, m)

    def test_duplicate_mode_ticket_rejects(self):
        m=copy.deepcopy(self.shadow)
        m["balance"]["tickets"][1]["combo"] = m["balance"]["tickets"][0]["combo"]
        with self.assertRaisesRegex(ValueError, "duplicate_mode_ticket"):
            _per_race(self.baseline, m)

    def test_invalid_ticket_rejects(self):
        m=copy.deepcopy(self.shadow)
        m["narrow"]["tickets"][0]["combo"] = "1-1-2"
        with self.assertRaisesRegex(ValueError, "bad_trifecta"):
            _per_race(self.baseline, m)

    def test_actual_archive_like_replay_stays_result_blind(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            path=root/"four_mode_forecasts"
            path.mkdir()
            for code, rates in (
                ("202611100101", RATES),
                ("202611100102", [5.2, 5.4, 7.7, 4.7, 6.1, 5.6]),
            ):
                (path/(code+".json")).write_text(
                    json.dumps(record(code, rates)), encoding="utf-8")
            out=audit_same_race_overlap("20261110", root)
            self.assertEqual(out["original_records"], 2)
            self.assertEqual(out["exact_v2_replays"], 2)
            self.assertEqual(len(out["by_race_full_tickets"]), 2)
            self.assertEqual(out["within_race_overlap"]["original"]["narrow_subset_hit_races"], 2)
            self.assertEqual(out["within_race_overlap"]["frozen_candidate"]["narrow_subset_hit_races"], 2)
            for flag in ("original_forecast_git_first_remote_acceptance_verified",
                         "official_beforeinfo_exhibition_odds120_verified",
                         "new_candidate_first_remote_acceptance_verified",
                         "actual_hit_rate_measured", "forced_ticket_diversification",
                         "formal", "promotion_allowed", "production_changed"):
                self.assertFalse(out[flag], flag)
            self.assertEqual(out["independently_scored_results"], 0)

    def test_mutated_archived_original_not_rebranded_as_replayed(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            path=root/"four_mode_forecasts"
            path.mkdir()
            r=record("202611100101", RATES)
            r["modes"]["hit"]["tickets"][0]["combo"] = "6-5-4"
            (path/"202611100101.json").write_text(json.dumps(r))
            with self.assertRaisesRegex(ValueError, "stored_original_replay_mismatch"):
                audit_same_race_overlap("20261110", root)

    def test_missing_and_invalid_day_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError, "missing_or_excess_day_originals"):
                audit_same_race_overlap("20261110", Path(d))
            with self.assertRaisesRegex(ValueError, "invalid_day"):
                audit_same_race_overlap("2026-11-10", Path(d))


if __name__ == "__main__":
    unittest.main()
