"""Tests for isolated, result-blind, position-sensitive four-mode candidate."""
import json
import math
from pathlib import Path
import tempfile
import unittest

from clean_four_modes import rank_modes
from research_model import probabilities
from four_mode_position_sensitive_shadow import (
    BASELINE_VERSION, MODES, VERSION, audit_day,
    shadow_modes, shadow_probabilities,
)

A = [5.01, 5.89, 6.28, 2.64, 6.09, 6.15]
B = [6.68, 3.82, 4.79, 4.80, 4.18, 5.53]


def combo(x):
    return "-".join(map(str, x))


class PositionShadowTests(unittest.TestCase):
    def test_board_complete_finite_unique_and_normalized(self):
        for rates in (A, B, [4.5] * 6, [1, 9, 3, 7, 2, 6]):
            rows = shadow_probabilities(rates)
            self.assertEqual(len(rows), 120)
            self.assertEqual(len({tuple(t) for t, _ in rows}), 120)
            self.assertTrue(all(p > 0 and math.isfinite(p) for _, p in rows))
            self.assertAlmostEqual(sum(p for _, p in rows), 1.0, places=10)

    def test_first_boat_mass_preserved_exactly_to_tolerance(self):
        for rates in (A, B):
            old = probabilities(rates)
            new = shadow_probabilities(rates)
            for head in range(1, 7):
                a = sum(p for t, p in old if t[0] == head)
                b = sum(p for t, p in new if t[0] == head)
                self.assertAlmostEqual(a, b, places=12)

    def test_change_is_from_second_third_strength_not_random_ticket_diversity(self):
        old_a = [combo(t) for t, _ in probabilities(A)[:5]]
        old_b = [combo(t) for t, _ in probabilities(B)[:5]]
        new_a = [combo(t) for t, _ in shadow_probabilities(A)[:5]]
        new_b = [combo(t) for t, _ in shadow_probabilities(B)[:5]]
        self.assertEqual(old_a[0], "1-2-4")
        self.assertEqual(old_b[0], "1-2-4")
        self.assertEqual(new_a[0], "1-2-3")
        self.assertEqual(new_b[0], "1-3-5")
        self.assertNotEqual(new_a[:5], new_b[:5])
        # Equal inputs should not produce arbitrary per-race id perturbation.
        equal = [5] * 6
        same = shadow_probabilities(equal)
        self.assertEqual([t for t, _ in same],
                         [t for t, _ in probabilities(equal)])

    def test_mode_budget_and_nonproduction_flags(self):
        out = shadow_modes(A)
        self.assertEqual(out["model_version"], VERSION)
        self.assertTrue(out["research_only"])
        self.assertFalse(out["formal"])
        self.assertFalse(out["production_forecast"])
        self.assertFalse(out["model_improvement_proven"])
        self.assertFalse(out["buy_recommendation"])
        self.assertEqual({k: len(v["tickets"]) for k, v in out["modes"].items()},
                         {"narrow": 5, "hit": 10, "balance": 16, "hole": 22})
        self.assertNotEqual(out["modes"]["narrow"]["tickets"][0]["combo"],
                            rank_modes(probabilities(A))["narrow"]["tickets"][0]["combo"])

    def test_reject_malformed_or_overflowing_inputs(self):
        for rates in ([5] * 5, [0, 5, 5, 5, 5, 5],
                      [float("nan"), 5, 5, 5, 5, 5],
                      [float("inf"), 5, 5, 5, 5, 5],
                      [40, 5, 5, 5, 5, 5],
                      ["5", 5, 5, 5, 5, 5]):
            with self.subTest(rates=rates):
                with self.assertRaises(ValueError):
                    shadow_probabilities(rates)

    def test_historical_audit_no_results_ever_needed_or_changed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            archive_dir = root / "four_mode_forecasts"
            archive_dir.mkdir()
            result_dir = root / "confirmed_results"
            result_dir.mkdir()
            (result_dir / "202611080101.json").write_text("not-a-json", encoding="utf-8")
            record = {
                "schema": "CLEAN_FOUR_MODES_PREDEADLINE_V1",
                "race_code": "202611080101",
                "model_version": BASELINE_VERSION,
                "generated_at_jst": "2026-11-08T09:15:00+09:00",
                "deadline_jst": "2026-11-08T12:15:00+09:00",
                "input_national_win_rates": A,
                "modes": rank_modes(probabilities(A)),
            }
            path = archive_dir / "202611080101.json"
            frozen = json.dumps(record)
            path.write_text(frozen, encoding="utf-8")
            out = audit_day("20261108", root)
            self.assertEqual(out["archived_files"], 1)
            self.assertEqual(out["compared"], 1)
            self.assertEqual(out["excluded"], 0)
            self.assertFalse(out["formal"])
            self.assertEqual(out["forward_holdout_scored"], 0)
            self.assertEqual(out["by_mode"]["hit"]["top1_changed"], 1)
            self.assertEqual(path.read_text(encoding="utf-8"), frozen)
            self.assertEqual((result_dir / "202611080101.json").read_text(), "not-a-json")

    def test_tampered_baseline_excluded_and_never_repaired(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            directory = root / "four_mode_forecasts"
            directory.mkdir()
            modes = rank_modes(probabilities(A))
            modes["hit"]["tickets"][0]["p"] += 0.01
            bad = {
                "schema": "CLEAN_FOUR_MODES_PREDEADLINE_V1",
                "race_code": "202611080101",
                "model_version": BASELINE_VERSION,
                "generated_at_jst": "2026-11-08T08:00:00+09:00",
                "deadline_jst": "2026-11-08T12:00:00+09:00",
                "input_national_win_rates": A,
                "modes": modes,
            }
            path = directory / "202611080101.json"
            original = json.dumps(bad)
            path.write_text(original)
            out = audit_day("20261108", root)
            self.assertEqual(out["compared"], 0)
            self.assertEqual(out["excluded"], 1)
            self.assertEqual(out["exclusions"]["baseline_not_reproduced"], 1)
            self.assertEqual(path.read_text(), original)

    def test_bad_day_fails_and_missing_day_does_not_fake_sample(self):
        with self.assertRaises(ValueError):
            audit_day("../results")
        with tempfile.TemporaryDirectory() as td:
            out = audit_day("20261108", td)
            self.assertEqual(out["compared"], 0)
            self.assertFalse(out["model_improvement_proven"])


if __name__ == "__main__":
    unittest.main()
