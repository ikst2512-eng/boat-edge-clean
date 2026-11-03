"""Retired one-day November 3 observation must never run on another date."""
import unittest
from pathlib import Path


WORKFLOW = Path(__file__).resolve().parent / ".github/workflows/official-three-original-t12-observation.yml"


class RetiredT12ObservationWorkflowTests(unittest.TestCase):
    def test_expired_cron_removed_but_manual_dispatch_retained(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertNotIn("\n  schedule:", text)
        self.assertNotIn("cron:", text)
        self.assertIn("\n  workflow_dispatch:", text)
        self.assertIn("race_code:", text)
        self.assertIn("RACE_CODE: ${{ github.event_name == 'workflow_dispatch' && inputs.race_code || matrix.race_code }}", text)

    def test_pr_runs_regressions_not_stale_live_race(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("workflow-regression:", text)
        self.assertIn("python -m unittest -v test_official_three_original_schedule_retirement", text)
        self.assertIn("  observe:\n    if: github.event_name == 'workflow_dispatch'", text)
        self.assertIn("  summarize:\n    if: github.event_name == 'workflow_dispatch' && always()", text)


if __name__ == "__main__":
    unittest.main()
