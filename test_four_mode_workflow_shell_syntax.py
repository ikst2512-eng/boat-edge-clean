"""Protect the capture publication script from invalid nested shell here-documents."""
import subprocess
import unittest
from pathlib import Path

WORKFLOW = Path(__file__).parent / ".github/workflows/four-mode-prospective-capture.yml"

class PublicationShellSyntaxTest(unittest.TestCase):
    def test_privileged_capture_only_runs_on_main_schedule_or_dispatch(self):
        # A non-main workflow_dispatch must never execute the job that can
        # git push HEAD:main or write append-only research evidence.
        text = WORKFLOW.read_text(encoding="utf-8")
        expected = (
            "  capture:\n"
            "    # workflow_dispatch can target a feature branch. Never let it enter the\n"
            "    # privileged forecast-publication path or attempt git push HEAD:main.\n"
            "    if: github.ref == 'refs/heads/main' && "
            "(github.event_name == 'schedule' || "
            "github.event_name == 'workflow_dispatch')"
        )
        self.assertIn(expected, text)
        self.assertIn("git push origin HEAD:main", text)
        # PRs can still test the code, but cannot run privileged capture.
        self.assertIn("  test:\n", text)

    def test_staging_shell_is_syntactically_valid(self):
        s=WORKFLOW.read_text(encoding="utf-8")
        start=s.index("      - name: Stage only immutable new forecasts and check receipt window")
        end=s.index("      - name: Freeze shadow after confirmed publication",start)
        segment=s[start:end]
        assert "        run: |\n" in segment
        lines=segment.split("        run: |\n",1)[1].splitlines()
        shell="\n".join(line[10:] if line.startswith("          ") else line for line in lines)+"\n"
        p=subprocess.run(["bash","-n"],input=shell,text=True,capture_output=True)
        self.assertEqual(p.returncode,0,p.stderr)

if __name__=="__main__":
    unittest.main()
