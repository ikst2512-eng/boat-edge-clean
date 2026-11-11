"""Result-blind position-exposure tests (never inspect real outcomes)."""
import json
import tempfile
import unittest
from pathlib import Path

from test_four_mode_all_mode_same_job_shadow import make_original
from four_mode_top1_head_exposure_audit import (
    audit, audit_files, position_delta,
)


def save(root, original):
    p = root / "four_mode_forecasts" / (original["race_code"] + ".json")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(original), encoding="utf-8")
    return p


class Top1HeadExposureTests(unittest.TestCase):
    def test_changed_exact_ticket_can_keep_same_winning_head_and_second(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            original = make_original()
            original["race_code"] = "202611080101"
            p = save(root, original)
            report = audit_files([p], "20261108", expected_minimum=1)
            mode = report["modes"]["hit"]
            self.assertEqual(mode["changed_exact_top1"], 1)
            self.assertEqual(mode["changed_first_boat"], 0)
            self.assertEqual(mode["changed_second_boat"], 0)
            self.assertEqual(mode["changed_third_boat"], 1)
            self.assertEqual(mode["swaps_same_first_second"], 1)
            self.assertEqual(mode["different_first_boat_in_original_top2"], 0)
            self.assertEqual(mode["original_top1_heads"], {"1": 1})
            self.assertEqual(mode["candidate_top1_heads"], {"1": 1})
            self.assertEqual(mode["original_top1_distinct_tickets"], 1)
            self.assertFalse(report["result_files_read"])
            self.assertFalse(report["formal"])
            self.assertFalse(report["model_improvement_proven"])

    def test_result_dir_presence_and_poison_never_changes_input_audit(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            raw = make_original()
            raw["race_code"] = "202611080101"
            p = save(root, raw)
            first = audit_files([p], "20261108", expected_minimum=1)
            results = root / "confirmed_results"
            results.mkdir()
            (results / (raw["race_code"]+".json")).write_text(
                "THIS_MUST_NEVER_BE_OPENED", encoding="utf-8"
            )
            second = audit_files([p], "20261108", expected_minimum=1)
            self.assertEqual(first, second)

    def test_position_delta_separates_head_and_second_and_third(self):
        self.assertEqual(position_delta("1-2-4", "1-2-3"), (False, False, True))
        self.assertEqual(position_delta("1-2-4", "3-1-4"), (True, True, False))
        self.assertEqual(position_delta("1-2-4", "1-2-4"), (False, False, False))
        with self.assertRaisesRegex(ValueError, "invalid_top1_combo"):
            position_delta("1-2-2", "1-2-4")

    def test_same_day_duplicate_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            raw = make_original()
            raw["race_code"] = "202611080101"
            p = save(root, raw)
            with self.assertRaisesRegex(ValueError, "unsafe_duplicate_or_invalid_original"):
                audit_files([p, p], "20261108", expected_minimum=1)

    def test_wrong_or_postrace_original_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            raw = make_original()
            raw["race_code"] = "202611080101"
            raw["finish_order"] = [1, 2, 3]
            p = save(root, raw)
            with self.assertRaisesRegex(ValueError, "postrace_content_in_forecast"):
                audit_files([p], "20261108", expected_minimum=1)

    def test_invalid_input_date_and_insufficient_full_day(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            raw = make_original()
            raw["race_code"] = "202611080101"
            p = save(root, raw)
            with self.assertRaisesRegex(ValueError, "not_frozen_discovery_date"):
                audit(root, "20261109")
            with self.assertRaisesRegex(ValueError, "incomplete_discovery_forecast_inventory"):
                audit(root, "20261108")
            with self.assertRaisesRegex(ValueError, "invalid_discovery_input"):
                audit_files([p], "20261109", expected_minimum=1)

    def test_mismatched_code_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            p = save(root, make_original())
            with self.assertRaisesRegex(ValueError, "unsafe_duplicate_or_invalid_original"):
                audit_files([p], "20261108", expected_minimum=1)


if __name__ == "__main__":
    unittest.main()
