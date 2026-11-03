"""Guard watchdog audit persistence without changing dispatch decisions."""
import ast
import re
import textwrap
import unittest
from pathlib import Path

WORKFLOW = Path(".github/workflows/four-mode-capture-watchdog.yml")


class WatchdogEvidenceContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = WORKFLOW.read_text(encoding="utf-8")
        match = re.search(r"^          python - <<'PY'\n(?P<code>.*?)^          PY\n",
                          cls.text, re.MULTILINE | re.DOTALL)
        if match is None:
            raise AssertionError("missing watchdog program")
        cls.script = textwrap.dedent(match.group("code"))
        ast.parse(cls.script)

    def test_original_dispatch_decisions_are_preserved(self):
        self.assertIn("should_dispatch(publication, now, os.environ[", self.script)
        self.assertIn('report["action"]="fallback_dispatch_accepted"', self.script)
        self.assertIn('report["action"]="no_dispatch"', self.script)
        self.assertIn('if response.status!=204:', self.script)

    def test_decision_artifact_is_bounded_and_contains_no_credentials(self):
        self.assertIn('"schema":"FOUR_MODE_WATCHDOG_DECISION_V1"', self.script)
        self.assertIn('"github_run_id":os.environ["GITHUB_RUN_ID"]', self.script)
        self.assertIn('"checked_at_utc":now.isoformat()', self.script)
        self.assertIn('**report', self.script)
        self.assertNotIn('**os.environ', self.script)
        self.assertNotIn('"token":', self.script)
        self.assertNotIn('"headers":', self.script)

    def test_report_uses_the_same_fourteen_minute_window_as_dispatch(self):
        # Prevent an audit from reporting obsolete 27/20-minute suppression
        # even while the live dispatch uses the new 14-minute windows.
        self.assertIn("<14*60", self.script)
        self.assertIn("< 14*60", self.script)
        self.assertIn("recent_minutes=14, cooldown_minutes=14", self.script)
        self.assertNotIn("27*60", self.script)
        self.assertNotIn("< 20*60]", self.script)
        self.assertIn('"older_active_runs_blocking"', self.script)
        self.assertIn("120*60", self.script)

    def test_upload_occurs_even_when_watchdog_fails(self):
        self.assertIn('if: always()', self.text)
        self.assertIn('name: four-mode-watchdog-decision-${{ github.run_id }}', self.text)
        self.assertIn('path: |\n            four-mode-evidence/watchdog-decision.json\n            four-mode-evidence/v2-nightly-decision.json', self.text)
        self.assertIn('retention-days: 14', self.text)


if __name__ == "__main__":
    unittest.main()
