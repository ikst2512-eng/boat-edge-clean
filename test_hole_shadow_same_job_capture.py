import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from hole_shadow_same_job_capture import capture_published

SHA = "a" * 40
CODE = "202611030101"


class SameJobTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.path = self.root / "publication.json"

    def put(self, **kwargs):
        data = {"outcome":"pushed_to_main","commit_sha":SHA,"added_forecasts":1}
        data.update(kwargs)
        self.path.write_text(json.dumps(data))

    def test_research_stage_outcomes_separate_from_v2_publication(self):
        workflow = (Path(__file__).parent /
                    ".github/workflows/four-mode-prospective-capture.yml").read_text(
                        encoding="utf-8")
        self.assertIn("id: third_rate_shadow", workflow)
        self.assertIn("id: hole_shadow", workflow)
        self.assertIn("THIRD_RATE_SHADOW_OUTCOME: ${{ steps.third_rate_shadow.outcome }}",
                      workflow)
        self.assertIn("HOLE_SHADOW_OUTCOME: ${{ steps.hole_shadow.outcome }}",
                      workflow)
        self.assertIn('"third_rate_shadow": os.environ["THIRD_RATE_SHADOW_OUTCOME"]',
                      workflow)
        self.assertIn('"hole_shadow": os.environ["HOLE_SHADOW_OUTCOME"]',
                      workflow)
        self.assertIn('states["publication"] = payload["outcome"]', workflow)

    def test_hole_shadow_step_is_independent_of_third_rate_step_failure(self):
        workflow = (Path(__file__).parent /
                    ".github/workflows/four-mode-prospective-capture.yml").read_text(
                        encoding="utf-8")
        third = workflow.index("      - name: Freeze third-place research shadow")
        hole = workflow.index("      - name: Freeze shadow after confirmed publication")
        stage = workflow.index("      - name: Record per-stage capture verdict")
        self.assertLess(third, hole)
        self.assertLess(hole, stage)
        block = workflow[hole:stage]
        self.assertIn("if: ${{ always() && github.event_name != 'pull_request' }}", block)
        self.assertIn("python hole_shadow_same_job_capture.py", block)

    def test_missing_or_unpublished_never_freezes(self):
        self.assertEqual(capture_published(self.root, self.path)["status"], "no_publication_evidence")
        self.put(outcome="no_eligible_candidates")
        self.assertEqual(capture_published(self.root, self.path)["status"], "not_published")

    def write_archive(self, code, content=b'{"v2":true}\\n'):
        file = self.root / "four_mode_forecasts" / (code + ".json")
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(content)
        return content

    def test_exact_publication_head_and_additions(self):
        self.put()
        raw = self.write_archive(CODE)
        def git(args):
            if args[0] == "rev-parse":
                return SHA
            if args[0] == "show":
                return raw
            return "four_mode_forecasts/" + CODE + ".json"
        with patch("hole_shadow_same_job_capture.freeze", return_value={
            "race_code": CODE, "status":"shadow_frozen_unverified"}) as f:
            data = capture_published(self.root, self.path,
                   datetime(2026,11,3,tzinfo=timezone.utc), git)
        self.assertEqual(data["frozen_count"], 1)
        self.assertFalse(data["formal"])
        self.assertFalse(data["independent_first_receipt_verified"])
        f.assert_called_once()

    def test_failed_one_race_preserves_another_valid_shadow(self):
        self.put(added_forecasts=2)
        code2 = "202611030102"
        raw = self.write_archive(CODE)
        self.write_archive(code2, raw)
        def git(args):
            if args[0] == "rev-parse":
                return SHA
            if args[0] == "show":
                return raw
            return "\n".join([
                "four_mode_forecasts/" + CODE + ".json",
                "four_mode_forecasts/" + code2 + ".json",
            ])
        def shadow(code, root, now):
            if code == CODE:
                raise ValueError("broken_model_input")
            return {"race_code": code, "status": "shadow_frozen_unverified"}
        with patch("hole_shadow_same_job_capture.freeze", side_effect=shadow):
            result = capture_published(
                self.root, self.path, datetime(2026, 11, 3, tzinfo=timezone.utc), git)
        self.assertEqual(result["published_new_count"], 2)
        self.assertEqual(result["frozen_count"], 1)
        self.assertEqual(result["validation_error_count"], 1)
        self.assertEqual(result["records"][0], {
            "race_code": CODE, "status": "validation_error", "error_type": "ValueError"})
        self.assertEqual(result["records"][1]["race_code"], code2)
        self.assertFalse(result["formal"])

    def test_shadow_cannot_return_wrong_race_identity(self):
        self.put()
        raw = self.write_archive(CODE)
        def git(args):
            if args[0] == "rev-parse":
                return SHA
            if args[0] == "show":
                return raw
            return "four_mode_forecasts/" + CODE + ".json"
        with patch("hole_shadow_same_job_capture.freeze", return_value={
                "race_code": "202611030102", "status": "shadow_frozen_unverified"}):
            result = capture_published(
                self.root, self.path, datetime(2026, 11, 3, tzinfo=timezone.utc), git)
        self.assertEqual(result["validation_error_count"], 1)
        self.assertEqual(result["frozen_count"], 0)
        self.assertEqual(result["records"][0]["status"], "validation_error")

    def test_modified_one_archive_isolated_without_erasing_other(self):
        self.put(added_forecasts=2)
        code2 = "202611030102"
        self.write_archive(CODE, b'{"altered":true}\\n')
        self.write_archive(code2, b'{"published":true}\\n')
        def git(args):
            if args[0] == "rev-parse":
                return SHA
            if args[0] == "show":
                return b'{"published":true}\\n'
            return ("four_mode_forecasts/" + CODE + ".json\n"
                    + "four_mode_forecasts/" + code2 + ".json")
        def freeze_valid(code, root, now):
            return {"race_code": code, "status": "shadow_frozen_unverified"}
        with patch("hole_shadow_same_job_capture.freeze", side_effect=freeze_valid) as f:
            result = capture_published(
                self.root, self.path, datetime(2026, 11, 3, tzinfo=timezone.utc), git)
        self.assertEqual(result["validation_error_count"], 1)
        self.assertEqual(result["frozen_count"], 1)
        self.assertEqual(result["records"][0]["status"], "validation_error")
        f.assert_called_once()

    def test_git_blob_comparison_keeps_trailing_newline(self):
        self.put()
        self.write_archive(CODE, b'{"published":true}\\n')
        def git(args):
            if args[0] == "rev-parse":
                return SHA
            if args[0] == "show":
                return b'{"published":true}'  # Not the same first-add bytes.
            return "four_mode_forecasts/" + CODE + ".json"
        with patch("hole_shadow_same_job_capture.freeze") as f:
            result = capture_published(
                self.root, self.path, datetime(2026, 11, 3, tzinfo=timezone.utc), git)
        self.assertEqual(result["validation_error_count"], 1)
        f.assert_not_called()

    def test_capture_cli_retains_nonzero_status_on_validation_errors(self):
        script = (Path(__file__).parent / "hole_shadow_same_job_capture.py").read_text()
        self.assertIn('if report.get("validation_error_count", 0):', script)
        self.assertIn("raise SystemExit(2)", script)

    def test_mismatched_publication_rejected(self):
        self.put()
        with self.assertRaises(ValueError):
            capture_published(self.root, self.path, git=lambda args: "b"*40)
        self.put(added_forecasts=2)
        with self.assertRaises(ValueError):
            capture_published(self.root, self.path, git=lambda args: SHA if args[0]=="rev-parse" else "four_mode_forecasts/"+CODE+".json")


if __name__ == "__main__":
    unittest.main()
