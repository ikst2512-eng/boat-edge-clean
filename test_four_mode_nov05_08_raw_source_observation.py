"""Regression tests: post-race published-source observation is not a collector."""
import hashlib
import json
import shutil
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from four_mode_nov05_08_daily_reference_audit import ROOT
from collect_clean_results import build_records
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

    def test_recovered_main_result_moves_from_public_only_to_persisted_exactly_once(self):
        # Simulate the real Nov8 recovery: the collector alone writes a new
        # immutable result. Independent research totals must remain constant.
        snapshot = source(
            (SAVED, "2026-11-08T15:40:22+09:00", 1, 2, 5),
            (PENDING, "2026-11-08T17:45:25+09:00", 1, 2, 4),
        )
        before = self.observe_one(snapshot)
        first = before["historical_original_union_reference_only"]
        self.assertEqual((first["persisted_result_count"],
                          first["newly_observed_public_unarchived_result_count"],
                          first["valid_saved_forecasts_with_persisted_or_public_result"]), (1, 1, 2))
        self.assertEqual(before["unarchived_published_shadow_only"]["persisted_reference_denominator"], 1)
        self.assertTrue(before["unarchived_published_shadow_only"]["separate_from_persisted_reference"])
        record = build_records(DAY, snapshot, CLOCK)[PENDING]
        path = self.root / "confirmed_results" / (PENDING + ".json")
        with path.open("x", encoding="utf-8") as out:
            json.dump(record, out, ensure_ascii=False)
        after = self.observe_one(snapshot)
        second = after["historical_original_union_reference_only"]
        self.assertEqual((second["persisted_result_count"],
                          second["newly_observed_public_unarchived_result_count"],
                          second["valid_saved_forecasts_with_persisted_or_public_result"]), (2, 0, 2))
        self.assertEqual(after["unarchived_published_shadow_only"]["races"], 0)
        self.assertEqual(after["unarchived_published_shadow_only"]["persisted_reference_denominator"], 2)
        self.assertTrue(after["unarchived_published_shadow_only"]["separate_from_persisted_reference"])
        for mode in ("narrow", "hit", "balance", "hole"):
            for key in ("top1", "top3", "top5", "top10"):
                x = first["modes"][mode]["top_hits_by_evidence_class"][key]
                y = second["modes"][mode]["top_hits_by_evidence_class"][key]
                self.assertEqual(x["combined_observed"], y["combined_observed"])
                self.assertEqual(x["saved_only"] + x["public_unarchived_only"], y["saved_only"])
                self.assertEqual(y["public_unarchived_only"], 0)
        self.assertEqual(after["source_conflict_count"], 0)
        self.assertFalse(after["formal"])
        self.assertEqual(after["prospective_candidate_pairs"], 0)

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

    def test_saved_plus_public_original_union_keeps_reference_separate(self):
        data = source(
            (SAVED, "2026-11-08T15:40:22+09:00", 1, 2, 5),
            (PENDING, "2026-11-08T17:45:25+09:00", 1, 2, 4),
        )
        report = self.observe_one(data)
        union = report["historical_original_union_reference_only"]
        self.assertEqual(union["status"], "COMPLETE_PUBLIC_SNAPSHOT_AND_CONFLICT_FREE")
        self.assertEqual((union["persisted_result_count"],
                          union["newly_observed_public_unarchived_result_count"],
                          union["valid_saved_forecasts_with_persisted_or_public_result"],
                          union["unknown_or_unobserved_result_count"],
                          union["eligible_archive_roster_without_exclusions"]), (1, 1, 2, 0, 2))
        top = union["modes"]["narrow"]["top_hits_by_evidence_class"]["top10"]
        self.assertEqual(top, {"saved_only": 1, "public_unarchived_only": 1, "combined_observed": 2})
        self.assertEqual(union["modes"]["narrow"][
            "top_pct_of_currently_observed_outcomes_reference_only"]["top10"], 100.0)
        self.assertEqual(report["reference_results_already_saved"], 1)
        self.assertEqual(report["unresolved_saved_result_files"], 1)
        self.assertTrue(union["do_not_replace_persisted_denominator"])
        self.assertTrue(union["not_official_and_not_prospective"])
        self.assertFalse(report["formal"])

    def test_unknown_source_row_is_not_scored_as_a_loss(self):
        report = self.observe_one(source(
            (SAVED, "2026-11-08T15:40:22+09:00", 1, 2, 5)))
        union = report["historical_original_union_reference_only"]
        self.assertEqual((union["valid_saved_forecasts_with_persisted_or_public_result"],
                          union["unknown_or_unobserved_result_count"]), (1, 1))
        lohi = union["modes"]["narrow"][
            "top_bounds_on_saved_archive_roster_not_confidence_intervals"]["top10"]
        self.assertEqual(lohi["lower_if_all_unknown_miss_pct"], 50.0)
        self.assertEqual(lohi["upper_if_all_unknown_hit_pct"], 100.0)
        self.assertFalse(report["model_promotion_allowed"])

    def test_finish_order_conflict_invalidates_union_status(self):
        report = self.observe_one(source(
            (SAVED, "2026-11-08T15:40:22+09:00", 1, 3, 5),
            (PENDING, "2026-11-08T17:45:25+09:00", 1, 2, 4)))
        union = report["historical_original_union_reference_only"]
        self.assertEqual(union["status"], "UNVERIFIED_INCOMPLETE_OR_CONFLICTING_SOURCE")
        self.assertEqual(report["source_conflict_count"], 1)
        self.assertTrue(union["incomplete_or_conflicting_source_cannot_be_promoted"])

    def test_timeout_invalidates_union_status_not_saved_data(self):
        report = observe(self.root, (DAY,), fetcher=lambda day: (_ for _ in ()).throw(
            TimeoutError("no source")))
        union = report["historical_original_union_reference_only"]
        self.assertEqual(union["status"], "UNVERIFIED_INCOMPLETE_OR_CONFLICTING_SOURCE")
        self.assertEqual(union["persisted_result_count"], 1)
        self.assertEqual(union["unknown_or_unobserved_result_count"], 1)
        self.assertFalse(report["formal"])

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
