"""Protect the capture publication script from invalid nested shell here-documents."""
import subprocess
import unittest
from pathlib import Path

WORKFLOW = Path(__file__).parent / ".github/workflows/four-mode-prospective-capture.yml"

class PublicationShellSyntaxTest(unittest.TestCase):
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
