"""Negative/positive gates for Nov5-8 read-only four-mode coverage audit."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from four_mode_nov05_08_daily_reference_audit import audit, ROOT

CODE = "202611080101"


class DailyReferenceAuditTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for sub in ("four_mode_forecasts", "confirmed_results"):
            (self.root / sub).mkdir()
            shutil.copyfile(ROOT / sub / (CODE + ".json"),
                            self.root / sub / (CODE + ".json"))

    def run_audit(self):
        return audit(self.root, ("20261108",))

    def test_real_original_and_independent_saved_result(self):
        result = self.run_audit()
        day = result["by_day"]["20261108"]
        self.assertEqual((day["forecast_files"], day["v2_archives"],
                          day["evaluated"], day["pending_result_count"],
                          day["excluded_count"]), (1, 1, 1, 0, 0))
        self.assertEqual(day["mode"]["narrow"]["top_hits"], {
            "top1": 0, "top3": 0, "top5": 1, "top10": 1})
        self.assertEqual(day["mode"]["hit"]["top_hits"]["top5"], 1)
        self.assertEqual(day["mode"]["balance"]["top_hits"]["top5"], 0)
        self.assertEqual(day["mode"]["balance"]["top_hits"]["top10"], 1)
        self.assertEqual(day["mode"]["hole"]["top_hits"]["top10"], 0)
        self.assertFalse(result["formal"])
        self.assertEqual(result["formal_count"], 0)
        self.assertFalse(result["model_improvement_proven"])
        self.assertFalse(result["result_source_bytes_reverified"])

    def test_missing_result_is_pending_not_a_loss(self):
        (self.root / "confirmed_results" / (CODE + ".json")).unlink()
        day = self.run_audit()["by_day"]["20261108"]
        self.assertEqual(day["evaluated"], 0)
        self.assertEqual(day["pending_result_codes"], [CODE])
        self.assertIsNone(day["mode"]["hit"]["top_pct"]["top10"])

    def test_untrusted_result_source_is_excluded(self):
        p = self.root / "confirmed_results" / (CODE + ".json")
        data = json.loads(p.read_text())
        data["source_url"] = "https://example.test/forged.csv"
        p.write_text(json.dumps(data))
        day = self.run_audit()["by_day"]["20261108"]
        self.assertEqual(day["evaluated"], 0)
        self.assertEqual(day["excluded_reasons"]["untrusted_result_or_source"], 1)
        self.assertEqual(day["pending_result_count"], 0)

    def test_result_known_before_deadline_is_excluded(self):
        p = self.root / "confirmed_results" / (CODE + ".json")
        data = json.loads(p.read_text())
        data["confirmed_at_jst"] = "2026-11-08T14:00:00+09:00"
        p.write_text(json.dumps(data))
        day = self.run_audit()["by_day"]["20261108"]
        self.assertEqual(day["evaluated"], 0)
        self.assertEqual(day["excluded_reasons"][
            "result_timestamp_not_post_deadline_or_collection"], 1)

    def test_other_model_version_not_pooled(self):
        p = self.root / "four_mode_forecasts" / (CODE + ".json")
        data = json.loads(p.read_text())
        data["model_version"] = "CLEAN_FOUR_MODES_V1_UNCALIBRATED"
        p.write_text(json.dumps(data))
        day = self.run_audit()["by_day"]["20261108"]
        self.assertEqual(day["evaluated"], 0)
        self.assertEqual(day["excluded_reasons"]["not_v2_model_version"], 1)

    def test_broken_ticket_budget_excluded(self):
        p = self.root / "four_mode_forecasts" / (CODE + ".json")
        data = json.loads(p.read_text())
        data["modes"]["hit"]["tickets"].pop()
        p.write_text(json.dumps(data))
        day = self.run_audit()["by_day"]["20261108"]
        self.assertEqual(day["evaluated"], 0)
        self.assertEqual(day["excluded_reasons"][
            "inconsistent_mode_ticket_budget"], 1)

    def test_bad_forecast_generation_time_excluded(self):
        p = self.root / "four_mode_forecasts" / (CODE + ".json")
        data = json.loads(p.read_text())
        data["generated_at_jst"] = "2026-11-08T15:22:00+09:00"
        p.write_text(json.dumps(data))
        day = self.run_audit()["by_day"]["20261108"]
        self.assertEqual(day["evaluated"], 0)
        self.assertEqual(day["excluded_reasons"]["invalid_saved_forecast"], 1)

    def test_invalid_input_days_refused(self):
        with self.assertRaisesRegex(ValueError, "invalid_days"):
            audit(self.root, ("20261108", "20261108"))
        with self.assertRaisesRegex(ValueError, "invalid_days"):
            audit(self.root, ("2026-11-08",))


    def test_missing_result_has_uncertainty_bounds_not_zero_hit_rate(self):
        (self.root / "confirmed_results" / (CODE + ".json")).unlink()
        report = self.run_audit()
        row = report["reference_overall"]["mode"]["hit"]
        bounds = row["top_pending_bounds"]["top10"]
        self.assertEqual((report["reference_overall"]["confirmed_denominator"],
                          report["reference_overall"]["pending_outcome_count"],
                          bounds["saved_valid_with_or_without_result"]), (0, 1, 1))
        self.assertEqual(bounds["lower_percent_all_pending_miss"], 0.0)
        self.assertEqual(bounds["upper_percent_all_pending_hit"], 100.0)
        self.assertIsNone(row["top_pct_confirmed_only"]["top10"])
        self.assertFalse(report["formal"])

    def test_original_same_race_top10_pair_partition(self):
        report = self.run_audit()
        pairs = report["reference_overall"]["same_race_original_top10_pairs"]
        self.assertEqual(pairs["narrow_vs_hit"]["both"], 1)
        self.assertEqual(pairs["hit_vs_balance"]["both"], 1)
        self.assertEqual(pairs["balance_vs_hole"]["left_only"], 1)
        self.assertEqual(sum(pairs["balance_vs_hole"].values()), 1)

    def test_full_ticket_coverage_separated_from_top10(self):
        report = self.run_audit()
        mode = report["reference_overall"]["mode"]
        self.assertEqual(mode["balance"]["full_list_covered"], 1)
        self.assertEqual(mode["balance"]["full_list_correct_beyond_top10"], 0)
        self.assertEqual(mode["hole"]["full_list_correct_beyond_top10"], 0)
        for value in mode.values():
            self.assertGreaterEqual(value["full_list_covered"],
                                    value["top_hits"]["top10"])

    def test_invalid_result_not_recast_as_pending_bounds(self):
        p = self.root / "confirmed_results" / (CODE + ".json")
        row = json.loads(p.read_text())
        row["source_sha256"] = "not_a_sha"
        p.write_text(json.dumps(row))
        report = self.run_audit()
        self.assertEqual(report["totals"]["excluded"], 1)
        self.assertEqual(report["reference_overall"]["known_plus_pending_denominator"], 0)
        self.assertEqual(report["reference_overall"]["pending_outcome_count"], 0)
        bounds = report["reference_overall"]["mode"]["hit"]["top_pending_bounds"]["top10"]
        self.assertIsNone(bounds["lower_percent_all_pending_miss"])
        self.assertIsNone(bounds["upper_percent_all_pending_hit"])


if __name__ == "__main__":
    unittest.main()
