import json
import tempfile
import unittest
from pathlib import Path

from scripts.report_four_mode_dispatch_publications import dispatch_history, inspect_dispatches

WF = "four-mode-prospective-capture.yml"


def run(id, event="workflow_dispatch", conclusion="success"):
    return {"id": id, "event": event, "workflow": WF,
            "created_at": "2026-11-03T06:24:08+00:00",
            "conclusion": conclusion}


class DispatchEvidenceTests(unittest.TestCase):
    def test_inspect_real_dispatch_not_schedule(self):
        history = {"recent_capture_runs": [run(9), run(8, event="schedule"), run(7, conclusion="failure")]}
        def download(run_id, root):
            self.assertIn(run_id, (9, 7))
            p = root / "four-mode-evidence"
            p.mkdir(parents=True)
            (p / "publication.json").write_text(
                json.dumps({"outcome": "no_eligible_candidates"}), encoding="utf-8")
            (p / "staging.json").write_text(json.dumps({"staged_valid": 0}), encoding="utf-8")
            (p / "source-links.json").write_text(json.dumps({
                "schema": "FOUR_MODE_LOCAL_SOURCE_LINK_REPORT_V2",
                "day_jst": "20261103",
                "publication_scope_status": "no_new_publication",
                "checked": 0, "hashes_present": 0}), encoding="utf-8")
        result = inspect_dispatches(history, download)
        self.assertEqual(result["dispatch_runs_checked"], 2)
        self.assertEqual([x["run_id"] for x in result["runs"]], [9, 7])
        self.assertEqual(result["runs"][0]["source_link_status"], "no_new_publication")
        self.assertEqual(result["runs"][0]["staged_valid"], 0)
        self.assertEqual(result["runs"][1]["capture_conclusion"], "failure")
        self.assertFalse(result["remote_main_verified"])

    def test_empty_dispatch_is_unproven(self):
        result = inspect_dispatches({"recent_capture_runs": [run(5, event="schedule")]},
                                    lambda *_: self.fail("no download"))
        self.assertEqual(result["dispatch_runs_checked"], 0)
        self.assertIsNone(result["claimed_added_forecasts_sum"])

    def test_missing_artifact_is_unknown_not_saved_zero(self):
        result = inspect_dispatches({"recent_capture_runs": [run(4)]},
                                    lambda *_: (_ for _ in ()).throw(OSError("artifact missing")), limit=1)
        self.assertEqual(result["dispatch_runs_checked"], 1)
        self.assertIsNone(result["runs"][0]["publication_outcome"])

    def test_reject_duplicate_and_mismatched_workflow(self):
        with self.assertRaises(ValueError):
            dispatch_history({"recent_capture_runs": [run(1), run(1)]})
        unexpected = run(3)
        unexpected["workflow"] = "other-workflow.yml"
        with self.assertRaises(ValueError):
            dispatch_history({"recent_capture_runs": [unexpected]})

    def test_limit_and_identity_rules(self):
        rows = dispatch_history({"recent_capture_runs": [run(3), run(2), run(1)]}, limit=2)
        self.assertEqual([x["id"] for x in rows["runs"]], [3, 2])
        with self.assertRaises(ValueError):
            dispatch_history({"recent_capture_runs": [run(True)]})

if __name__ == "__main__":
    unittest.main()
