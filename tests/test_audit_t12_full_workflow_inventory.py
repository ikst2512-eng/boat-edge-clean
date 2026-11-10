"""Fail-closed immutable complete Git workflow inventory regression cases."""
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.audit_t12_full_workflow_inventory import (
    PINNED, _events, inspect, scan,
)


def registry():
    return {
        ".github/workflows/official-pair.yml": b"""name: pair
on:
  schedule:
    - cron: '*/5 0-12 * * *'
  workflow_dispatch:
jobs:
  run:
    steps:
      - run: python -m scripts.capture_joint_preview_batch
""",
        ".github/workflows/three-manual.yml": b"""name: manual triad
on:
  workflow_dispatch:
    inputs:
      race_code:
        required: true
jobs:
  observe:
    steps:
      - run: python -m scripts.observe_three_official_t12_originals
""",
        ".github/workflows/racelist-manual.yml": b"""name: manual racelist
on: [push, workflow_dispatch]
jobs:
  observe:
    steps:
      - run: |
          from scripts.capture_official_racelist_receipt import capture
""",
        ".github/workflows/other.yml": b"""name: comments
on:
  push:
    paths:
      - .github/workflows/other.yml
jobs:
  test:
    steps:
      - run: echo 'a schedule is not an on event'
""",
    }


class RealPinnedWorkflowTree(unittest.TestCase):
    def test_full_inventory_respects_actual_top_level_events(self):
        result = inspect(registry())
        self.assertEqual(result["github_workflow_files_examined"], 4)
        self.assertEqual(result["workflows_with_classifiable_on_declaration"], 4)
        self.assertEqual(result["workflows_with_declared_schedule_event"], 1)
        self.assertEqual(result["direct_executable_reference_match_count"], 0)
        self.assertEqual(result["declared_scheduled_workflow_paths"],
                         [".github/workflows/official-pair.yml"])
        self.assertFalse(result["absence_of_any_indirect_source_capture_proven"])
        self.assertFalse(result["formal"])
        self.assertIsNone(result["formal_accuracy_denominator"])

    def test_direct_source_reference_in_scheduled_yaml_is_not_silently_skipped(self):
        rows = registry()
        rows[".github/workflows/official-pair.yml"] += (
            b"      - run: python -m scripts.observe_three_official_t12_originals\n")
        report = inspect(rows)
        self.assertEqual(report["direct_executable_reference_match_count"], 1)
        self.assertEqual(len(report[
            "scheduled_workflows_with_direct_racelist_or_tri_capture_text"]), 1)
        self.assertFalse(report["formal"])

    def test_unknown_on_event_form_is_reported_unclassified(self):
        rows = registry()
        rows[".github/workflows/official-pair.yml"] = (
            b"name: unknown\non: {schedule: [{cron: '*/5 * * * *'}]}\n")
        report = inspect(rows)
        self.assertIn(".github/workflows/official-pair.yml",
                      report["unclassified_workflow_on_declarations"])
        self.assertEqual(report["workflows_with_declared_schedule_event"], 0)

    def test_inline_schedule_event_is_counted(self):
        rows = registry()
        rows[".github/workflows/official-pair.yml"] = (
            b"name: inline\non: [schedule, workflow_dispatch]\n")
        report = inspect(rows)
        self.assertEqual(report["workflows_with_declared_schedule_event"], 1)

    def test_fake_schedule_word_inside_body_does_not_count(self):
        self.assertEqual(_events("name: nope\non:\n  push:\njobs:\n  a:\n    schedule: yes\n"),
                         ["push"])
        self.assertEqual(_events("name: noop\non: push\njobs:\n"), ["push"])

    def test_repeated_and_missing_on_declarations_are_not_success(self):
        self.assertIsNone(_events("on:\n  schedule:\non:\n  push:\n"))
        self.assertIsNone(_events("name: nope\njobs:\n  run:\n"))
        self.assertIsNone(_events("on:\n  schedule:\n  schedule:\n"))

    def test_invalid_git_registry_path_cannot_pass(self):
        for path in ("../workflow.yml", ".github/workflows/../a.yml",
                     ".github/workflows/subfolder/a.yml",
                     ".github/workflows/a.py"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                inspect({path: b"on:\n  schedule:\n"})

    def test_absent_or_corrupt_git_source_rejected(self):
        for contents in (None, "", b"", b"\xff\xfe", b"x"*150001):
            with self.subTest(contents=str(contents)[:18]), self.assertRaises(ValueError):
                inspect({".github/workflows/a.yml": contents})

    def test_no_empty_workflow_tree(self):
        with self.assertRaises(ValueError):
            inspect({})
        with self.assertRaises(ValueError):
            inspect(None)

    def test_pinned_commit_hash_required(self):
        for ref in ("main", "", "f"*64, None):
            with self.subTest(ref=ref), self.assertRaises(ValueError):
                inspect(registry(), pinned=ref)

    def test_all_git_blob_sha1_fields_match_exact_source_bytes(self):
        data = registry()
        result = inspect(data)
        for row in result["files"]:
            raw = data[row["path"]]
            real = hashlib.sha1(
                b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
            self.assertEqual(row["git_blob_sha1"], real)

    def test_wrong_checked_out_git_ref_fails_before_tree_read(self):
        with tempfile.TemporaryDirectory() as p:
            with patch("scripts.audit_t12_full_workflow_inventory._git",
                       return_value=b"f"*40+b"\n"):
                with self.assertRaises(ValueError):
                    scan(p)

    def test_missing_local_git_checkout_fails(self):
        with self.assertRaises(ValueError):
            scan("/not-present-git-checkout-for-t12")

    def test_bounded_inventory_does_not_promote_formal_accuracy(self):
        report = inspect(registry())
        for flag in ("workflow_scheduling_executions_proven",
                     "official_three_originals_replayed_by_this_audit",
                     "forecast_model_consumption_proven",
                     "first_forecast_remote_git_acceptance_proven",
                     "t12_eligible", "accuracy_scoring_allowed", "formal"):
            self.assertFalse(report[flag], flag)
        self.assertEqual(report["new_formal_certifications"], 0)


if __name__ == "__main__":
    unittest.main()
