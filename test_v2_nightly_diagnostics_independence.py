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

    def test_combined_capture_inventory_is_valid_json_at_runtime(self):
        import json
        import re
        import subprocess
        import sys
        import tempfile
        import textwrap

        workflow = Path(".github/workflows/v2-predeclared-shadow-research.yml").read_text(
            encoding="utf-8")
        match = re.search(r"          python - <<'PY'\n(.*?)\n          PY", workflow, re.S)
        self.assertIsNotNone(match)
        source = textwrap.dedent(match.group(1))
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            expected = [
                {"databaseId": 1001, "event": "schedule"},
                {"databaseId": 1002, "event": "workflow_dispatch"},
            ]
            (root / "v2_capture_scheduled.json").write_text(
                json.dumps(expected[:1]), encoding="utf-8")
            (root / "v2_capture_dispatched.json").write_text(
                json.dumps(expected[1:]), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, "-c", source], cwd=root,
                check=False, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            output = (root / "v2_capture_run_inventory.json").read_text(
                encoding="utf-8")
            self.assertEqual(json.loads(output), expected)
            self.assertTrue(output.endswith("\n"))
            self.assertFalse(output.endswith("\\\\n"))

    def test_capture_inventory_excludes_pr_traffic_before_combining(self):
        workflow = Path(".github/workflows/v2-predeclared-shadow-research.yml").read_text(
            encoding="utf-8")
        for event, destination in (
            ("schedule", "v2_capture_scheduled.json"),
            ("workflow_dispatch", "v2_capture_dispatched.json"),
        ):
            with self.subTest(event=event):
                self.assertIn(
                    "--event " + event
                    + " --limit 500 --json databaseId,event,createdAt,headBranch,conclusion > "
                    + destination,
                    workflow,
                )
                self.assertIn("            " + destination + "\n", workflow)
        self.assertIn('rows.extend(data)', workflow)
        self.assertIn('json.dumps(rows, sort_keys=True)', workflow)

    def test_nightly_piped_scorer_failure_cannot_be_hidden_by_tee(self):
        import subprocess

        workflow = Path(".github/workflows/v2-predeclared-shadow-research.yml").read_text(
            encoding="utf-8")
        self.assertIn(
            "  evaluate:\n    runs-on: ubuntu-latest\n"
            "    timeout-minutes: 30\n"
            "    # Explicit bash turns on pipefail: a failed scorer before `| tee` fails CI.\n"
            "    defaults:\n      run:\n        shell: bash", workflow)
        self.assertIn("four_mode_v2_frozen_third_nightly.py --run-inventory", workflow)
        self.assertIn("| tee v2_frozen_third_nightly.log", workflow)
        self.assertIn("| tee v2_third_rate_durable_ledger.log", workflow)
        self.assertIn("| tee v2_third_ledger_reconciliation.log", workflow)
        result = subprocess.run(
            ["bash", "-e", "-o", "pipefail", "-c", "python -c 'raise SystemExit(17)' | tee /dev/null"],
            check=False, capture_output=True, text=True)
        self.assertEqual(result.returncode, 17)




if __name__ == "__main__":
    unittest.main()
