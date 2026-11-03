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

    def test_dispatch_propagates_research_error_independently_of_push(self):
        def download(_, root):
            p = root / "four-mode-evidence"
            p.mkdir(parents=True)
            (p / "publication.json").write_text(json.dumps({
                "outcome": "pushed_to_main", "added_forecasts": 2,
                "commit_sha": "a" * 40}), encoding="utf-8")
            (p / "stages.json").write_text(json.dumps({
                "publication": "pushed_to_main",
                "third_rate_shadow": "success",
                "hole_shadow": "failure"}), encoding="utf-8")
        result = inspect_dispatches({"recent_capture_runs": [run(9)]}, download)
        self.assertEqual(result["claimed_added_forecasts_sum"], 2)
        self.assertEqual(result["third_rate_shadow_failure_runs"], [])
        self.assertEqual(result["hole_shadow_failure_runs"], [9])
        self.assertEqual(result["runs"][0]["hole_shadow_outcome"], "failure")

    def test_dispatch_research_coverage_unknown_not_zero_success(self):
        def download(_, root):
            p = root / "four-mode-evidence"
            p.mkdir(parents=True)
            (p / "publication.json").write_text(
                json.dumps({"outcome": "no_eligible_candidates"}), encoding="utf-8")
        result = inspect_dispatches({"recent_capture_runs": [run(9)]}, download)
        self.assertEqual(result["research_stage_coverage"]["third_rate_shadow"]["unknown"], 1)
        self.assertEqual(result["research_stage_coverage"]["hole_shadow"]["unknown"], 1)
        self.assertEqual(result["research_stage_coverage"]["hole_shadow"]["checked"], 1)

    def test_empty_dispatch_is_unproven(self):
        result = inspect_dispatches({"recent_capture_runs": [run(5, event="schedule")]},
                                    lambda *_: self.fail("no download"))
        self.assertEqual(result["dispatch_runs_checked"], 0)
        self.assertIsNone(result["claimed_added_forecasts_sum"])
        self.assertEqual(result["research_stage_coverage"]["third_rate_shadow"]["checked"], 0)
        self.assertEqual(result["research_stage_coverage"]["hole_shadow"]["checked"], 0)

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

    def test_earliest_fallback_push_not_hidden_by_eight_later_noops(self):
        # Latest first: six-run reporting would miss the early push.
        runs = [run(120 - i) for i in range(9)]
        def download(run_id, root):
            p = root / "four-mode-evidence"
            p.mkdir(parents=True)
            payload = ({"outcome": "pushed_to_main",
                        "added_forecasts": 3, "commit_sha": "a" * 40}
                       if run_id == 112 else {"outcome": "no_eligible_candidates"})
            (p / "publication.json").write_text(json.dumps(payload), encoding="utf-8")
        result = inspect_dispatches({"recent_capture_runs": runs}, download)
        self.assertEqual(result["dispatch_runs_checked"], 9)
        self.assertEqual(result["runs"][-1]["run_id"], 112)
        self.assertEqual(result["runs_claiming_push"], 1)
        self.assertEqual(result["claimed_added_forecasts_sum"], 3)

    def test_dispatch_evidence_bound_remains_explicit(self):
        history = {"recent_capture_runs": [run(200 - i) for i in range(15)]}
        checked = []
        result = inspect_dispatches(history, lambda rid, _: checked.append(rid))
        self.assertEqual(result["dispatch_runs_checked"], 12)
        self.assertEqual(result["history_runs_omitted"], 3)
        self.assertEqual(len(checked), 12)
        self.assertFalse(result["remote_main_verified"])

    def test_limit_and_identity_rules(self):
        rows = dispatch_history({"recent_capture_runs": [run(3), run(2), run(1)]}, limit=2)
        self.assertEqual([x["id"] for x in rows["runs"]], [3, 2])
        with self.assertRaises(ValueError):
            dispatch_history({"recent_capture_runs": [run(True)]})

if __name__ == "__main__":
    unittest.main()
