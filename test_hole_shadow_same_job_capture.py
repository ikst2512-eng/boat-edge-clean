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

    def test_exact_publication_head_and_additions(self):
        self.put()
        def git(args):
            if args[0] == "rev-parse":
                return SHA
            return "four_mode_forecasts/" + CODE + ".json"
        with patch("hole_shadow_same_job_capture.freeze", return_value={
            "status":"shadow_frozen_unverified"}) as f:
            data = capture_published(self.root, self.path,
                   datetime(2026,11,3,tzinfo=timezone.utc), git)
        self.assertEqual(data["frozen_count"], 1)
        self.assertFalse(data["formal"])
        self.assertFalse(data["independent_first_receipt_verified"])
        f.assert_called_once()

    def test_mismatched_publication_rejected(self):
        self.put()
        with self.assertRaises(ValueError):
            capture_published(self.root, self.path, git=lambda args: "b"*40)
        self.put(added_forecasts=2)
        with self.assertRaises(ValueError):
            capture_published(self.root, self.path, git=lambda args: SHA if args[0]=="rev-parse" else "four_mode_forecasts/"+CODE+".json")


if __name__ == "__main__":
    unittest.main()
