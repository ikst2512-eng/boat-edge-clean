"""One-day, research-only fallback must not be mistaken for an external timer."""
import unittest
from pathlib import Path

PATH = ".github/workflows/t12-kiryu12-upstream-recovery-20261103.yml"


class KiryuResearchUpstreamRecoveryContract(unittest.TestCase):
    def test_only_actual_successful_upstream_schedule_writes_research_evidence(self):
        workflow = Path(PATH).read_text()
        self.assertIn("workflow_run:", workflow)
        self.assertIn("types: [completed]", workflow)
        self.assertIn("Four-mode prospective capture (research only)", workflow)
        self.assertIn("workflow_run.event == 'schedule'", workflow)
        self.assertIn("workflow_run.conclusion == 'success'", workflow)
        self.assertIn("workflow_run.conclusion == 'failure'", workflow)
        self.assertNotIn("workflow_run.conclusion == 'cancelled'", workflow)
        self.assertIn("workflow_run.event == 'schedule'", workflow)
        self.assertIn("workflow_run.head_branch == 'main'", workflow)
        self.assertNotIn("\n  schedule:", workflow)
        self.assertNotIn("\n  push:", workflow)
        self.assertIn("202611030112", workflow)
        self.assertIn("scripts.gate_kiryu12_upstream_recovery import check_window", workflow)
        self.assertIn("check_window(datetime.now(timezone.utc)", workflow)
        self.assertIn("UPSTREAM_STARTED_AT", workflow)
        self.assertIn("research-t12-external-evidence", workflow)
        self.assertIn("scripts.run_external_three_t12", workflow)
        self.assertIn("does not prove T12 reliability", workflow)
        self.assertNotIn("git push", workflow)
        self.assertIn("scripts.gate_kiryu12_upstream_recovery import check_window", workflow)
        self.assertIn("python -m scripts.run_external_three_t12", workflow)


if __name__ == "__main__":
    unittest.main()
