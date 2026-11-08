"""Regression tests: post-race published-source observation is not a collector."""
import hashlib
import json
import shutil
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from four_mode_nov05_08_daily_reference_audit import ROOT
from four_mode_nov05_08_raw_source_observation import compare_one, observe

DAY = "20261108"
SAVED = "202611080101"
PENDING = "202611080106"
CLOCK = datetime.fromisoformat("2026-11-08T20:40:00+09:00")


def source(*rows):
    cols = "レースコード,取得日時,1着_艇番,2着_艇番,3着_艇番\n"
    return (cols + "".join(
        f"{code},{when},{a},{b},{c}\n" for code, when, a, b, c in rows
    )).encode("utf-8")


class OriginalSourceObservationTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        for directory in ("four_mode_forecasts", "confirmed_results"):
            (self.root / directory).mkdir()
        for code in (SAVED, PENDING):
            shutil.copyfile(ROOT / "four_mode_forecasts" / (code + ".json"),
                            self.root / "four_mode_forecasts" / (code + ".json"))
        shutil.copyfile(ROOT / "confirmed_results" / (SAVED + ".json"),
                        self.root / "confirmed_results" / (SAVED + ".json"))
        self.old_result = (self.root / "confirmed_results" / (SAVED + ".json")).read_bytes()

    def observe_one(self, blob):
        return observe(self.root, (DAY,), fetcher=lambda d: (blob, CLOCK))

    def test_published_row_missing_archive_not_scored_or_saved(self):
        blob = source(
            (SAVED, "2026-11-08T15:40:22+09:00", 1, 2, 5),
            (PENDING, "2026-11-08T17:45:25+09:00", 4, 1, 6),
        )
        report = self.observe_one(blob)
        self.assertEqual(report["status"], "ALL_SOURCE_SNAPSHOTS_OBSERVED")
        row = report["by_day"][DAY]
        self.assertEqual(row["pending_classes"]["valid_published_row_not_yet_archived"], 1)
        self.assertEqual(row["pending_codes_by_class"]["valid_published_row_not_yet_archived"], [PENDING])
        self.assertEqual(row["archived_to_current_comparison"]["finish_order_matches_current_source"], 1)
        self.assertEqual(row["archived_to_current_comparison"]["historical_whole_file_digest_differs"], 1)
        self.assertEqual(row["current_snapshot_sha256"], hashlib.sha256(blob).hexdigest())
        self.assertFalse((self.root / "confirmed_results" / (PENDING + ".json")).exists())
        self.assertEqual((self.root / "confirmed_results" / (SAVED + ".json")).read_bytes(),
                         self.old_result)
        self.assertEqual(report["unresolved_saved_result_files"], 1)
        self.assertEqual(report["prospective_candidate_pairs"], 0)
        self.assertFalse(report["formal"])

    def test_unarchived_published_result_scores_original_only_and_never_replaces_saved_denominator(self):
        # This is deliberately NOT a new selector or a formal paired outcome.
        snapshot = source(
            (SAVED, "2026-11-08T15:40:22+09:00", 1, 2, 5),
            (PENDING, "2026-11-08T17:45:25+09:00", 1, 2, 4),
        )
        report = self.observe_one(snapshot)
        preview = report["unarchived_published_shadow_only"]
        self.assertEqual(preview["races"], 1)
        self.assertEqual(preview["race_codes"], [PENDING])
        self.assertEqual(preview["denominator"], 1)
        for mode in ("narrow", "hit", "balance"):
            self.assertEqual(preview["original_saved_top_hits"][mode]["top1"], 1)
        self.assertEqual(preview["original_saved_top_hits"]["hole"]["top1"], 0)
        self.assertEqual(report["reference_results_already_saved"], 1)
        self.assertEqual(report["unresolved_saved_result_files"], 1)
        self.assertFalse(preview["eligible_for_formal_admission"])
        self.assertFalse(report["formal"])
        self.assertEqual(report["prospective_candidate_pairs"], 0)
        self.assertFalse((self.root / "confirmed_results" / (PENDING + ".json")).exists())

    def test_exact_public_bytes_saved_for_replay_in_separate_folder_only(self):
        data = source((PENDING, "2026-11-08T17:45:25+09:00", 4, 1, 6))
        folder = self.root / "ci-evidence" / "published"
        report = observe(self.root, (DAY,), fetcher=lambda day: (data, CLOCK), raw_dir=folder)
        self.assertEqual(report["public_raw_csv_retained_day_codes"], [DAY])
        self.assertTrue(report["public_raw_csv_retained_for_exact_replay"])
        self.assertTrue(report["public_raw_csv_evidence_is_ci_artifact_only"])
        self.assertEqual((folder / (DAY + ".csv")).read_bytes(), data)
        self.assertEqual((self.root / "confirmed_results" / (SAVED + ".json")).read_bytes(), self.old_result)
        self.assertFalse((self.root / "confirmed_results" / (PENDING + ".json")).exists())
        # Retry must fail closed instead of silently overwriting observed raw bytes.
        retry = observe(self.root, (DAY,), fetcher=lambda day: (data, CLOCK), raw_dir=folder)
        self.assertEqual(retry["status"], "SOURCE_OBSERVATION_INCOMPLETE")
        self.assertIn("FileExistsError", retry["source_errors"][DAY]["type"])

    def test_absent_row_is_not_in_published_csv(self):
        row = self.observe_one(source((SAVED, "2026-11-08T15:40:22+09:00", 1, 2, 5)))["by_day"][DAY]
        self.assertEqual(row["pending_classes"]["not_in_published_csv"], 1)
        self.assertEqual(row["pending_classes"]["valid_published_row_not_yet_archived"], 0)

    def test_unfinished_finish_is_not_three_boat_result(self):
        row = self.observe_one(source((PENDING, "2026-11-08T17:45:25+09:00", 4, 1, "")))["by_day"][DAY]
        self.assertEqual(row["pending_classes"]["invalid_or_unfinished_finish"], 1)
        self.assertFalse((self.root / "confirmed_results" / (PENDING + ".json")).exists())

    def test_future_source_acquisition_timestamp_never_admitted(self):
        row = self.observe_one(source((PENDING, "2026-11-08T20:50:00+09:00", 4, 1, 6)))["by_day"][DAY]
        self.assertEqual(row["pending_classes"]["future_source_timestamp"], 1)

    def test_pre_deadline_stamp_never_admitted(self):
        row = self.observe_one(source((PENDING, "2026-11-08T17:10:00+09:00", 4, 1, 6)))["by_day"][DAY]
        self.assertEqual(row["pending_classes"]["source_timestamp_not_post_deadline"], 1)

    def test_finish_conflict_is_not_hidden_by_whole_file_sha_drift(self):
        row = self.observe_one(source(
            (SAVED, "2026-11-08T15:40:22+09:00", 1, 3, 5),
            (PENDING, "2026-11-08T17:45:25+09:00", 4, 1, 6),
        ))
        self.assertEqual(row["source_conflict_count"], 1)
        self.assertTrue(row["source_finish_order_conflicts_need_manual_review"])
        self.assertEqual(row["by_day"][DAY]["finish_conflict_race_codes"], [SAVED])

    def test_duplicate_source_race_is_observation_error(self):
        data = source(
            (PENDING, "2026-11-08T17:45:25+09:00", 4, 1, 6),
            (PENDING, "2026-11-08T17:45:26+09:00", 4, 1, 6),
        )
        output = self.observe_one(data)
        self.assertEqual(output["status"], "SOURCE_OBSERVATION_INCOMPLETE")
        self.assertIn("duplicate source result", output["source_errors"][DAY]["reason"])
        self.assertEqual(output["source_observation_days"], 0)
        self.assertEqual(output["unresolved_saved_result_files"], 1)

    def test_404_or_timeout_not_called_verified(self):
        def broken(day):
            raise TimeoutError("source temporarily unreachable")
        result = observe(self.root, (DAY,), fetcher=broken)
        self.assertEqual(result["status"], "SOURCE_OBSERVATION_INCOMPLETE")
        self.assertEqual(result["source_observation_days"], 0)
        self.assertEqual(result["source_errors"][DAY]["type"], "TimeoutError")
        self.assertFalse(result["model_promotion_allowed"])


if __name__ == "__main__":
    unittest.main()
