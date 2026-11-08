"""Offline review gates for source-vs-stored read-only, nonformal audit."""
import json
import shutil
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from four_mode_nov05_08_daily_reference_audit import ROOT
from four_mode_result_raw_csv_audit import evaluate

DAY = "20261108"
KNOWN = DAY + "0101"
PENDING = DAY + "0106"
NOW = datetime.fromisoformat("2026-11-08T20:16:00+09:00")
HEADER = "レースコード,取得日時,1着_艇番,2着_艇番,3着_艇番\n"
SAVED = (KNOWN + ",2026-11-08T15:40:22.979278+09:00,1,2,5\n")
ADDED = (PENDING + ",2026-11-08T17:45:25.514493+09:00,4,1,6\n")


class RawResultSourceResearchAudit(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        for sub in ("four_mode_forecasts", "confirmed_results"):
            (self.root / sub).mkdir()
        for code in (KNOWN, PENDING):
            shutil.copyfile(ROOT / "four_mode_forecasts" / (code + ".json"),
                            self.root / "four_mode_forecasts" / (code + ".json"))
        shutil.copyfile(ROOT / "confirmed_results" / (KNOWN + ".json"),
                        self.root / "confirmed_results" / (KNOWN + ".json"))

    def run_with(self, rows):
        return evaluate(self.root, {DAY: (HEADER + rows).encode("utf-8")},
                        observed_at=NOW, days=(DAY,))

    def test_valid_unpersisted_is_not_scored(self):
        report = self.run_with(SAVED + ADDED)
        row = report["by_day"][DAY]
        self.assertEqual(row["saved_result_rows_matched_current_csv"], 1)
        self.assertEqual(row["pending_classification_counts"],
                         {"valid_source_three_finish_unpersisted": 1})
        self.assertEqual(row["pending_codes_by_class"][
            "valid_source_three_finish_unpersisted"], [PENDING])
        self.assertEqual(report["frozen_original_result_reference"]["evaluated"], 1)
        self.assertTrue(report["candidate_not_scored"])
        self.assertEqual(report["formal_count"], 0)

    def test_missing_source_is_not_miss(self):
        x = self.run_with(SAVED)
        self.assertEqual(x["by_day"][DAY]["pending_classification_counts"],
                         {"not_in_published_csv": 1})
        self.assertFalse(x["model_improvement_proven"])

    def test_three_finisher_incomplete_is_not_scoreable(self):
        x = self.run_with(SAVED + ADDED.replace(",4,1,6", ",4,1,"))
        self.assertEqual(x["by_day"][DAY]["pending_classification_counts"],
                         {"invalid_or_unfinished_finish_not_scoreable": 1})

    def test_duplicate_source_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate source result"):
            self.run_with(SAVED + ADDED + ADDED)

    def test_confirmed_stored_result_conflict_exposed(self):
        x = self.run_with(SAVED.replace(",1,2,5", ",1,2,3") + ADDED)
        self.assertEqual(x["by_day"][DAY][
            "saved_result_rows_disagree_or_not_present"], [KNOWN])
        self.assertEqual(x["by_day"][DAY][
            "saved_result_rows_matched_current_csv"], 0)

    def test_source_clock_must_follow_deadline_for_pending(self):
        x = self.run_with(SAVED + ADDED.replace(
            "2026-11-08T17:45:25.514493+09:00",
            "2026-11-08T13:00:00+09:00"))
        self.assertEqual(x["by_day"][DAY]["pending_classification_counts"],
                         {"source_clock_not_after_deadline": 1})

    def test_unknown_days_are_refused(self):
        with self.assertRaisesRegex(ValueError, "incomplete_raw_source_roster"):
            evaluate(self.root, {}, observed_at=NOW, days=(DAY,))

    def test_untrusted_saved_result_is_not_pending(self):
        path = self.root / "confirmed_results" / (KNOWN + ".json")
        obj = json.loads(path.read_text())
        obj["source_sha256"] = "corrupt"
        path.write_text(json.dumps(obj))
        with self.assertRaisesRegex(
            ValueError, "saved_forecast_or_result_excluded_manual_review"
        ):
            self.run_with(SAVED + ADDED)


if __name__ == "__main__":
    unittest.main()
