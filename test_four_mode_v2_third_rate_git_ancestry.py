import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from four_mode_v2_third_rate_git_ancestry import (
    FUTURE_START, audit, verify_shadow_cohort,
)

CODE = "202611040101"
NAME = "four_mode_forecasts/" + CODE + ".json"
SHA = "a" * 40


def make_root(td):
    root = Path(td)
    folder = root / "four_mode_forecasts"
    folder.mkdir()
    (folder / (CODE + ".json")).write_text('{"safe":true}')
    return root


def fake_git(*, timestamp="2026-11-04T10:30:00+09:00",
             original=b'{"safe":true}', history=True, shallow=False):
    def run(root, *args):
        if args[:2] == ("rev-parse", "--is-shallow-repository"):
            return b"true\n" if shallow else b"false\n"
        if args[0] == "log":
            return ((SHA + "\n" + NAME + "\n").encode() if history else b"")
        if args[:3] == ("show", "-s", "--format=%cI"):
            return timestamp.encode()
        if args[0] == "show" and args[1] == SHA + ":" + NAME:
            return original
        raise AssertionError(args)
    return run


def archive(*_):
    return 200, {
        "model_version": "CLEAN_FOUR_MODES_V2_PROVISIONAL_UNCALIBRATED",
        "deadline_jst": "2026-11-04T11:00:00+09:00",
    }


def confirmed(*_):
    return {"status": "historical_comparison_only"}


class ThirdRateGitAncestryTests(unittest.TestCase):
    def test_no_future_archives_is_not_verified_holdout(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "four_mode_forecasts").mkdir()
            report = audit(root, git=fake_git())
            self.assertEqual(report["status"], "no_future_v2_archives")
            self.assertEqual(report["future_result_paired"], 0)
            self.assertFalse(report["independent_remote_first_seen_verified"])
            self.assertFalse(report["production_promotion_allowed"])

    def test_git_first_add_before_t_minus_12_is_only_local_history(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_root(td)
            with patch("four_mode_v2_third_rate_git_ancestry.archived_four_modes",
                       side_effect=archive), patch(
                       "four_mode_v2_third_rate_git_ancestry.compare_race",
                       side_effect=confirmed):
                report = audit(root, git=fake_git())
            self.assertEqual(report["future_result_paired"], 1)
            self.assertEqual(report["future_result_paired_race_codes"], [CODE])
            self.assertEqual(report["first_add_before_t_minus_12_count"], 1)
            self.assertEqual(report["rows"][0]["status"],
                             "git_first_add_before_t_minus_12")
            self.assertEqual(report["rows"][0]["first_add_commit_sha"], SHA)
            self.assertEqual(report["by_day"]["20261104"]["paired_result"], 1)
            self.assertFalse(report["independent_cutoff_publication_verified"])
            self.assertFalse(report["production_promotion_allowed"])

    def test_git_first_add_after_t_minus_12_must_not_pass(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_root(td)
            with patch("four_mode_v2_third_rate_git_ancestry.archived_four_modes",
                       side_effect=archive), patch(
                       "four_mode_v2_third_rate_git_ancestry.compare_race",
                       side_effect=confirmed):
                report = audit(root, git=fake_git(timestamp="2026-11-04T10:52:01+09:00"))
            self.assertEqual(report["first_add_before_t_minus_12_count"], 0)
            self.assertEqual(report["first_add_after_t_minus_12_count"], 1)

    def test_original_blob_change_detected_even_with_early_commit(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_root(td)
            with patch("four_mode_v2_third_rate_git_ancestry.archived_four_modes",
                       side_effect=archive), patch(
                       "four_mode_v2_third_rate_git_ancestry.compare_race",
                       side_effect=confirmed):
                report = audit(root, git=fake_git(original=b'{"modified":true}'))
            self.assertEqual(report["first_add_original_blob_mismatch_count"], 1)
            self.assertEqual(report["first_add_before_t_minus_12_count"], 0)

    def test_missing_first_add_does_not_infer_success(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_root(td)
            with patch("four_mode_v2_third_rate_git_ancestry.archived_four_modes",
                       side_effect=archive), patch(
                       "four_mode_v2_third_rate_git_ancestry.compare_race",
                       side_effect=confirmed):
                report = audit(root, git=fake_git(history=False))
            self.assertEqual(report["missing_or_ambiguous_first_add_count"], 1)
            self.assertEqual(report["first_add_before_t_minus_12_count"], 0)

    def test_shallow_checkout_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_root(td)
            report = audit(root, git=fake_git(shallow=True))
            self.assertEqual(report["status"], "incomplete_git_history")
            self.assertEqual(report["unverifiable_count"], 1)
            self.assertFalse(report["checkout_git_history_complete"])

    def test_equal_counts_different_race_codes_rejected(self):
        audit_report = {"future_result_paired": 1,
                        "future_result_paired_race_codes": [CODE]}
        shadow = {"date_separated_forward_reference": {
            "start_day_jst": FUTURE_START, "paired": 1,
            "paired_race_codes": ["202611040102"]}}
        with self.assertRaisesRegex(ValueError, "forward_race_identity_mismatch"):
            verify_shadow_cohort(audit_report, shadow)

    def test_duplicate_or_missing_race_ids_rejected(self):
        result = {"future_result_paired": 2,
                  "future_result_paired_race_codes": [CODE, CODE]}
        shadow = {"date_separated_forward_reference": {
            "start_day_jst": FUTURE_START, "paired": 2,
            "paired_race_codes": [CODE, "202611040102"]}}
        with self.assertRaisesRegex(ValueError, "invalid_forward_race_roster"):
            verify_shadow_cohort(result, shadow)
        result["future_result_paired_race_codes"] = [CODE]
        with self.assertRaisesRegex(ValueError, "invalid_forward_race_roster"):
            verify_shadow_cohort(result, shadow)

    def test_development_day_race_in_forward_roster_rejected(self):
        result = {"future_result_paired": 1,
                  "future_result_paired_race_codes": ["202611030101"]}
        shadow = {"date_separated_forward_reference": {
            "start_day_jst": FUTURE_START, "paired": 1,
            "paired_race_codes": ["202611030101"]}}
        with self.assertRaisesRegex(ValueError, "invalid_forward_race_roster"):
            verify_shadow_cohort(result, shadow)

    def test_future_shadow_result_cohort_must_reconcile(self):
        stub = {"future_result_paired": 1,
                "future_result_paired_race_codes": [CODE]}
        shadow = {"date_separated_forward_reference": {
            "start_day_jst": FUTURE_START, "paired": 1,
            "paired_race_codes": [CODE]}}
        self.assertTrue(verify_shadow_cohort(stub, shadow))
        shadow["date_separated_forward_reference"]["paired"] = 2
        with self.assertRaises(ValueError):
            verify_shadow_cohort(stub, shadow)
        shadow["date_separated_forward_reference"]["paired"] = 1
        shadow["date_separated_forward_reference"]["start_day_jst"] = "20261103"
        with self.assertRaises(ValueError):
            verify_shadow_cohort(stub, shadow)


if __name__ == "__main__":
    unittest.main()
