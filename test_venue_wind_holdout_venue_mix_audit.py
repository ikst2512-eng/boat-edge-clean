"""Research holdout arithmetic, reconciliation, and non-causal status tests."""
import copy
import json
import unittest
from pathlib import Path

from venue_wind_holdout_venue_mix_audit import analyze

ROOT = Path(__file__).resolve().parent / "docs" / "research"
HISTORY = ROOT / "venue_wind_202608_202610_24venues_research_only.json"
HOLDOUT = ROOT / "venue_wind_nov01_05_out_of_period_research_only.json"
BANDS = ("0-2m", "3-4m", "5m+")


def load_inputs():
    return (json.loads(HISTORY.read_text(encoding="utf-8")),
            json.loads(HOLDOUT.read_text(encoding="utf-8")))


def fake_group(n, c1):
    # Fictional reproducible fixture with full six-course and direction counts.
    return {
        "n": n, "winner_course_counts": [c1, n-c1, 0, 0, 0, 0],
        "winning_method_counts": {"逃げ": c1, "差し": n-c1},
        "wind_direction_raw_counts": {"1": n},
    }


def synthetic():
    venues = {f"{i:02d}": {b: fake_group(0, 0) for b in BANDS}
              for i in range(1, 25)}
    # Identical calm/mid historical rates within each venue: no historic wind contrast.
    histories = []
    for i in range(1, 25):
        code = f"{i:02d}"
        base = 80 if i == 1 else 20 if i == 2 else 50
        histories.append({
            "code": code,
            "wind_bands": {
                b: {"n": 100, "actual_course1_first_pct": base} for b in BANDS
            },
        })
    venues["01"]["0-2m"] = fake_group(10, 8)
    venues["02"]["0-2m"] = fake_group(10, 2)
    venues["01"]["3-4m"] = fake_group(10, 8)
    venues["02"]["3-4m"] = fake_group(30, 6)
    groups = {}
    for band in BANDS:
        n = sum(v[band]["n"] for v in venues.values())
        won = sum(v[band]["winner_course_counts"][0] for v in venues.values())
        groups[band] = fake_group(n, won)
    return (
        {"period": "2026-08-01 to 2026-10-31",
         "official_binary_reconciliation": False, "venues": histories},
        {"period": "2026-11-01..2026-11-05",
         "post_race_weather": True, "approved_for_prediction": False,
         "official_result_reconciled": False,
         "validation": {"input_rows": 60, "accepted": 60, "excluded": 0},
         "national": groups, "venues": venues},
    )


class VenueWindHoldoutMixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.history, cls.holdout = load_inputs()

    def test_archived_november_counts_and_venue_mix(self):
        result = analyze(self.history, self.holdout)
        groups = result["groups"]
        self.assertEqual([groups[b]["n"] for b in BANDS], [547, 180, 29])
        self.assertEqual([groups[b]["winner_course1_count"] for b in BANDS], [326, 95, 14])
        self.assertEqual(groups["0-2m"]["old_calm_pct_reweighted_to_holdout_venue_mix"], 57.0)
        self.assertEqual(groups["3-4m"]["old_calm_pct_reweighted_to_holdout_venue_mix"], 54.88)
        self.assertEqual(groups["3-4m"]["old_same_band_pct_reweighted_to_holdout_venue_mix"], 53.63)
        self.assertEqual(groups["3-4m"]["raw_vs_holdout_calm_pt"], -6.82)
        self.assertEqual(groups["3-4m"]["venue_composition_only_shift_pt"], -2.11)
        self.assertEqual(groups["3-4m"]["remainder_not_attributable_to_wind_pt"], -4.71)
        self.assertEqual(groups["5m+"]["raw_vs_holdout_calm_pt"], -11.32)
        self.assertEqual(groups["5m+"]["venue_composition_only_shift_pt"], -2.9)
        self.assertEqual(groups["5m+"]["observed_ci95_pct"], [31.39, 65.57])
        self.assertFalse(groups["5m+"]["national_descriptive_min_n_met"])
        self.assertEqual(groups["5m+"]["holdout_venue_comparison_eligible"], [])
        self.assertFalse(result["predeadline_input_approved"])
        self.assertFalse(result["forecast_improvement_proven"])

    def test_venue_composition_can_create_false_wind_contrast(self):
        history, holdout = synthetic()
        result = analyze(history, holdout, national_min_n=1, venue_min_n=1)
        self.assertEqual(result["groups"]["3-4m"]["raw_vs_holdout_calm_pt"], -15.0)
        self.assertEqual(result["groups"]["3-4m"]["venue_composition_only_shift_pt"], -15.0)
        self.assertEqual(result["groups"]["3-4m"]["remainder_not_attributable_to_wind_pt"], 0.0)
        self.assertEqual(result["groups"]["3-4m"]["old_same_band_pct_reweighted_to_holdout_venue_mix"], 35.0)
        self.assertEqual(result["groups"]["3-4m"]["holdout_venue_comparison_eligible"], ["01", "02"])

    def test_bad_course_totals_fail_closed(self):
        bad = copy.deepcopy(self.holdout)
        bad["national"]["5m+"]["winner_course_counts"][0] += 1
        with self.assertRaisesRegex(ValueError, "national_course_reconciliation_failed"):
            analyze(self.history, bad)

    def test_bad_venue_direction_totals_fail_closed(self):
        bad = copy.deepcopy(self.holdout)
        bad["venues"]["03"]["5m+"]["wind_direction_raw_counts"]["8"] = 999
        with self.assertRaisesRegex(ValueError, "venue_direction_reconciliation_failed"):
            analyze(self.history, bad)

    def test_result_weather_never_claims_predicted_weather(self):
        bad = copy.deepcopy(self.holdout)
        bad["approved_for_prediction"] = True
        with self.assertRaisesRegex(ValueError, "holdout_is_not_confirmed_research_only"):
            analyze(self.history, bad)

    def test_changed_period_rejected(self):
        bad = copy.deepcopy(self.holdout)
        bad["period"] = "2026-08-01..2026-11-05"
        with self.assertRaisesRegex(ValueError, "holdout_period_not_fixed"):
            analyze(self.history, bad)


if __name__ == "__main__":
    unittest.main()
