"""Regression guard for race-scoped T-12 dispatch serialization."""
from pathlib import Path
import unittest


class ConcurrencyTests(unittest.TestCase):
    def test_race_dispatch_serialized_without_cancellation(self):
        workflow = Path(".github/workflows/official-joint-t12-dispatch.yml").read_text()
        block = workflow.split("\nconcurrency:\n", 1)[1].split("\njobs:", 1)[0]
        self.assertIn("inputs.race_code", block)
        self.assertIn("github.event_name == 'workflow_dispatch'", block)
        self.assertIn("github.event.pull_request.number", block)
        self.assertIn("cancel-in-progress: false", block)


if __name__ == "__main__":
    unittest.main()
