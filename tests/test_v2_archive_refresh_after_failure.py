"""Regression guard: scheduled archive audit must refresh main after upstream failures."""
import unittest
from pathlib import Path


class ArchiveRefreshFailureIndependenceTest(unittest.TestCase):
    def test_scheduled_refresh_ignores_upstream_failure_without_running_on_pr(self):
        workflow = Path(".github/workflows/four-mode-schedule-inventory.yml").read_text(encoding="utf-8")
        self.assertIn(
            "name: Refresh remote main before final Git publication audit\n"
            "        if: always() && github.event_name == 'schedule' && github.ref == 'refs/heads/main'",
            workflow,
        )
        self.assertIn(
            "name: Confirm today's first-add archive presence in checked-out Git main\n"
            "        if: always()",
            workflow,
        )
        self.assertIn("git fetch --no-tags origin main", workflow)
        self.assertIn("git checkout --detach FETCH_HEAD", workflow)
        self.assertIn("name: four-mode-schedule-history", workflow)


if __name__ == "__main__":
    unittest.main()
