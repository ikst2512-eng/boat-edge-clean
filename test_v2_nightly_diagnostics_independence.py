"""Guard independent nightly third-rate evidence checks after upstream failures."""
import unittest
from pathlib import Path


class NightlyDiagnosticsIndependenceTest(unittest.TestCase):
    def test_both_nightly_evidence_sources_run_after_prior_failures(self):
        workflow = Path(".github/workflows/v2-predeclared-shadow-research.yml").read_text(
            encoding="utf-8")
        steps = (
            "Read actual capture artifact inventory for frozen-only third-rate scoring",
            "Score preserved third-rate original evidence from durable branch",
            "Reconcile frozen captured race IDs with durable ledger entries",
        )
        for name in steps:
            with self.subTest(step=name):
                self.assertIn(
                    "name: " + name + "\n"
                    "        if: ${{ always() && github.event_name != 'pull_request' }}",
                    workflow,
                )
        self.assertIn("v2_capture_run_inventory.json", workflow)
        self.assertIn("v2_third_rate_durable_ledger.json", workflow)
        self.assertIn("v2_third_ledger_reconciliation.json", workflow)
        self.assertIn("if: always()\n        with:\n          name: v2-predeclared-shadow-", workflow)


if __name__ == "__main__":
    unittest.main()
