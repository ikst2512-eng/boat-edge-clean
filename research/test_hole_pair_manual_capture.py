"""Synthetic research-only gateway driver tests: no API, no results, no push."""
import hashlib
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from hole_future_pair_precommit import JST
from research import hole_pair_manual_capture as m
from research.test_hole_pair_cross_batch_roster import frozen

DAY = "20261109"
MAIN = "a" * 40
PATH1 = "four_mode_forecasts/202611090101.json"
PATH2 = "four_mode_forecasts/202611090102.json"
NOW = datetime(2026, 11, 9, 10, 52, 0, tzinfo=JST)
DONE = datetime(2026, 11, 9, 10, 52, 1, tzinfo=JST)


class ManualCaptureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.reads = []
        self.calls = []

    def fixture_raw(self, path):
        return ('{"race_code":"' + Path(path).stem + '"}').encode()

    def read(self, path):
        self.reads.append(path)
        self.assertTrue(path.startswith("four_mode_forecasts/"))
        self.assertNotIn("confirmed_results", path)
        return self.fixture_raw(path)

    def blob(self, path):
        raw = self.fixture_raw(path)
        return hashlib.sha1(
            b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
        ).hexdigest()

    def freezer(self, code, root):
        self.calls.append(code)
        record = frozen(code)
        record.pop("source_git_blob_sha1")  # freezer() leaves blob for capture driver
        record["source_sha256"] = hashlib.sha256(
            (Path(root) / "four_mode_forecasts" / (code + ".json")).read_bytes()
        ).hexdigest()
        return record

    def run_capture(self, paths=None, freezer=None, **changes):
        return m.capture(
            changes.get("day", DAY), changes.get("source_sha", MAIN),
            paths if paths is not None else [PATH1],
            changes.get("read_source", self.read), changes.get("read_blob", self.blob),
            freezer or self.freezer, self.root,
            current_time=changes.get("current_time", NOW),
            start_time=changes.get("start_time", NOW),
            finish_time=changes.get("finish_time", DONE),
        )

    def test_one_frozen_future_record_and_full_immutable_main_roster(self):
        out = self.run_capture()
        self.assertEqual(out["frozen_count"], 1)
        self.assertEqual(out["eligible_forecasts_examined"], 1)
        self.assertEqual(out["source_forecast_codes"], ["202611090101"])
        self.assertEqual(out["records"][0]["source_git_blob_sha1"], self.blob(PATH1))
        self.assertTrue(out["source_snapshot_coverage"]["source_snapshot_race_coverage_complete"])
        self.assertFalse(out["source_snapshot_coverage"]["entire_day_or_official_schedule_complete_verified"])
        self.assertFalse(out["formal"])
        self.assertFalse(out["independent_first_receipt_verified"])
        self.assertFalse(out["prospective_validation"])
        self.assertFalse(out["production_forecast_changed"])
        self.assertEqual(self.reads, [PATH1])
        self.assertFalse((self.root / "confirmed_results").exists())

    def test_exclusions_are_exact_ids_and_never_become_candidate(self):
        def freezer(code, root):
            if code.endswith("02"):
                return {"race_code": code, "status": "after_t_minus_12", "formal": False}
            return self.freezer(code, root)
        out = self.run_capture([PATH1, PATH2], freezer)
        self.assertEqual(out["frozen_count"], 1)
        self.assertEqual(out["excluded_by_reason"], {"after_t_minus_12": 1})
        self.assertEqual(out["excluded_race_codes_by_reason"], {"after_t_minus_12": ["202611090102"]})
        self.assertEqual(out["source_forecast_codes"], ["202611090101", "202611090102"])

    def test_unknown_status_cannot_silently_hide_a_forecast(self):
        with self.assertRaisesRegex(ValueError, "unknown_freezer_exclusion_reason"):
            self.run_capture(freezer=lambda code, root: {"race_code": code, "status": "winner_known"})

    def test_duplicate_or_unsorted_paths_fail_before_reading_any_source(self):
        for paths, error in (
            ([PATH1, PATH1], "unsafe_or_duplicate_source_paths"),
            ([PATH2, PATH1], "source_paths_not_sorted"),
        ):
            with self.subTest(paths=paths), self.assertRaisesRegex(ValueError, error):
                self.run_capture(paths)
        self.assertEqual(self.reads, [])

    def test_paths_must_be_canonical_same_day_forecasts(self):
        for bad in ("confirmed_results/202611090101.json",
                    "four_mode_forecasts/202611080101.json",
                    "four_mode_forecasts/202611090101.txt",
                    "four_mode_forecasts/202611090101.json/extra"):
            with self.subTest(bad=bad), self.assertRaisesRegex(ValueError, "untrusted_source_path"):
                self.run_capture([bad])

    def test_original_checkout_conflict_rejected(self):
        p = self.root / PATH1
        p.parent.mkdir(parents=True)
        p.write_bytes(b"different source")
        with self.assertRaisesRegex(ValueError, "research_checkout_has_conflicting_forecast"):
            self.run_capture()

    def test_wrong_git_blob_is_rejected_before_freezer_or_write(self):
        with self.assertRaisesRegex(
                ValueError, "immutable_main_source_blob_content_mismatch"):
            self.run_capture(read_blob=lambda _: "b" * 40)
        self.assertEqual(self.calls, [])

    def test_mismatched_frozen_source_hash_fails_closed(self):
        def lying_freezer(code, root):
            record = self.freezer(code, root)
            record["source_sha256"] = "0" * 64
            return record
        with self.assertRaisesRegex(
                ValueError, "frozen_candidate_original_source_sha256_mismatch"):
            self.run_capture(freezer=lying_freezer)

    def test_verified_source_blob_and_candidate_hash_same_exact_bytes(self):
        out = self.run_capture()
        record = out["records"][0]
        raw = self.fixture_raw(PATH1)
        self.assertEqual(record["source_git_blob_sha1"], self.blob(PATH1))
        self.assertEqual(record["source_sha256"], hashlib.sha256(raw).hexdigest())

    def test_manual_gateway_requires_typed_ack_and_dispatch(self):
        with patch.object(m, "datetime") as clock:
            clock.now.return_value = NOW
            for event, ack in (
                ("pull_request", m.ACK),
                ("schedule", m.ACK),
                ("workflow_dispatch", ""),
                ("workflow_dispatch", "CAPTURE_PRODUCTION"),
            ):
                with self.subTest(event=event, ack=ack), self.assertRaisesRegex(
                        ValueError, "manual_research_dispatch_not_authorized"):
                    m.manual_only_guard(DAY, event, ack)
            self.assertEqual(m.manual_only_guard(DAY, "workflow_dispatch", m.ACK), NOW)

    def test_backdated_and_future_days_fail_without_source_read(self):
        with patch.object(m, "datetime") as clock:
            clock.now.return_value = NOW
            for day in ("20261108", "20261110"):
                with self.subTest(day=day), self.assertRaisesRegex(
                        ValueError, "backdated_or_noncurrent_capture_day"):
                    m.manual_only_guard(day, "workflow_dispatch", m.ACK)
        with self.assertRaisesRegex(ValueError, "capture_day_not_current_future_jst"):
            self.run_capture(day="20261110")
        self.assertFalse(self.reads)

    def test_crossing_midnight_or_reversing_batch_clock_fails(self):
        for finish in (
            datetime(2026, 11, 9, 10, 51, 59, tzinfo=JST),
            datetime(2026, 11, 10, 0, 0, 1, tzinfo=JST),
        ):
            with self.subTest(finish=finish), self.assertRaisesRegex(
                    ValueError, "capture_crossed_day_or_clock_reversed"):
                self.run_capture(finish_time=finish)

    def test_invalid_frozen_method_or_blob_does_not_make_candidate_artifact(self):
        def bad(code, root):
            r = self.freezer(code, root)
            r["method_source_sha256"] = "0" * 64
            return r
        with self.assertRaisesRegex(ValueError, "untrusted_candidate_claim_or_method"):
            self.run_capture(freezer=bad)

    def test_symlink_to_forecast_cannot_be_followed(self):
        p = self.root / PATH1
        p.parent.mkdir(parents=True)
        other = self.root / "other"
        other.write_bytes(b"untrusted bytes")
        p.symlink_to(other)
        with self.assertRaisesRegex(ValueError, "unsafe_forecast_symlink"):
            self.run_capture()

    def test_workflow_only_dispatches_with_typed_jst_ack_and_fails_missing_artifact(self):
        workflow = (
            Path(__file__).resolve().parent.parent /
            ".github/workflows/hole-future-pair-precommit.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("  workflow_dispatch:\n    inputs:\n", workflow)
        self.assertIn("      capture_day_jst:\n", workflow)
        self.assertIn("      acknowledgement:\n", workflow)
        self.assertIn("        required: true\n", workflow)
        self.assertIn(
            "HOLE_RESEARCH_CAPTURE_DAY: ${{ inputs.capture_day_jst }}", workflow)
        self.assertIn(
            "HOLE_RESEARCH_MANUAL_ACK: ${{ inputs.acknowledgement }}", workflow)
        self.assertIn(
            'python research/hole_pair_manual_capture.py --capture-day '
            '"$HOLE_RESEARCH_CAPTURE_DAY" --output research_candidate_freeze.json',
            workflow)
        self.assertIn(
            "          name: hole-future-pair-precutoff-candidates\n"
            "          path: research_candidate_freeze.json\n"
            "          if-no-files-found: error", workflow)
        self.assertNotIn("for name in sorted(paths):", workflow)
        # A PR test may never make a new candidate artifact.
        self.assertIn(
            "- name: Freeze future race candidates from immutable main forecasts "
            "(research only)\n"
            "        if: github.event_name == 'workflow_dispatch'", workflow)

    def test_empty_current_main_snapshot_not_reported_as_official_day(self):
        out = self.run_capture([])
        self.assertEqual(out["frozen_count"], 0)
        self.assertFalse(out["source_snapshot_coverage"]["entire_day_or_official_schedule_complete_verified"])
        self.assertFalse(out["formal"])


if __name__ == "__main__":
    unittest.main()
