"""Result-blind archived feature-field coverage audit tests."""
import json
from pathlib import Path
import tempfile
import unittest

from clean_four_modes import rank_modes
from research_model import probabilities
from position_sensitive_feature_inventory import (
    FIELDS, audit_feature_day, feature_presence,
)

RATES = [5.01, 5.89, 6.28, 2.64, 6.09, 6.15]


def original_record():
    return {
        "schema": "CLEAN_FOUR_MODES_PREDEADLINE_V1",
        "race_code": "202611080101",
        "model_version": "CLEAN_FOUR_MODES_V2_PROVISIONAL_UNCALIBRATED",
        "generated_at_jst": "2026-11-08T08:00:00+09:00",
        "deadline_jst": "2026-11-08T12:00:00+09:00",
        "target_rates_not_proven": True,
        "validated": False,
        "input_national_win_rates": list(RATES),
        "beforeinfo": "optional_not_in_snapshot",
        "source_sha256": {"title": "a" * 64, "race_cards": "b" * 64},
        "modes": rank_modes(probabilities(RATES)),
    }


class FeatureInventoryTests(unittest.TestCase):
    def test_only_recorded_fields_not_verified_provenance(self):
        r = original_record()
        observed = feature_presence(r)
        self.assertTrue(observed["national_win_rates_six"])
        self.assertTrue(observed["public_title_card_digests_recorded"])
        self.assertFalse(observed["beforeinfo_structured"])
        self.assertFalse(observed["exhibition_six_structured"])
        self.assertFalse(observed["actual_entry_six_structured"])
        self.assertFalse(observed["motor_six_structured"])
        self.assertFalse(observed["exhibition_ST_six_structured"])
        self.assertFalse(observed["wind_structured"])
        self.assertFalse(observed["odds_120_structured"])

    def test_structured_presence_does_not_create_formal_status(self):
        r = original_record()
        r["beforeinfo"] = {"foo": 1}
        r["exhibition_six"] = [{}, {}, {}, {}, {}, {}]
        r["odds_120"] = {str(k): 1.0 for k in range(120)}
        observed = feature_presence(r)
        self.assertTrue(observed["beforeinfo_structured"])
        self.assertTrue(observed["exhibition_six_structured"])
        self.assertTrue(observed["odds_120_structured"])
        # This is ONLY schema presence, not a credible official board.

    def test_daily_archive_replay_ignores_results_and_preserves_original(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            f = root / "four_mode_forecasts"
            f.mkdir()
            (root / "confirmed_results").mkdir()
            bad_result = root / "confirmed_results" / "202611080101.json"
            bad_result.write_text("NOT JSON")
            path = f / "202611080101.json"
            frozen = json.dumps(original_record(), sort_keys=True)
            path.write_text(frozen)
            out = audit_feature_day("20261108", root)
            self.assertEqual(out["archived_files"], 1)
            self.assertEqual(out["compared"], 1)
            self.assertEqual(out["excluded"], 0)
            self.assertEqual(out["recorded_top_level_feature_counts"][
                "national_win_rates_six"], 1)
            self.assertEqual(out["recorded_top_level_feature_counts"][
                "public_title_card_digests_recorded"], 1)
            self.assertEqual(out["recorded_top_level_feature_counts"][
                "beforeinfo_structured"], 0)
            self.assertFalse(out["formal_official_beforeinfo_six_odds120_verified"])
            self.assertFalse(out["independent_candidate_first_remote_receipt_verified"])
            self.assertFalse(out["model_improvement_proven"])
            self.assertEqual(path.read_text(), frozen)
            self.assertEqual(bad_result.read_text(), "NOT JSON")
            modified = original_record()
            modified["modes"]["hit"]["tickets"][0]["p"] = -50
            path.write_text(json.dumps(modified))
            report = audit_feature_day("20261108", root)
            self.assertEqual(report["compared"], 0)
            self.assertEqual(report["excluded"], 1)
            self.assertEqual(report["exclusion_reasons"]["original_board_replay_failed"], 1)

    def test_empty_day_and_invalid_path_do_not_fake_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            report = audit_feature_day("20261108", td)
            self.assertEqual(report["archived_files"], 0)
            self.assertEqual(report["recorded_top_level_feature_counts"][
                "national_win_rates_six"], 0)
            self.assertFalse(report["formal"])
        for day in ("../data", "2026118", "20261108.json"):
            with self.assertRaises(ValueError):
                audit_feature_day(day)


if __name__ == "__main__":
    unittest.main()
