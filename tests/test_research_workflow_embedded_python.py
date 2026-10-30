"""Validate Python heredocs embedded in the snapshot GitHub Actions workflow."""
import ast
import re
from pathlib import Path
import unittest

WORKFLOW = Path(__file__).resolve().parents[1] / ".github/workflows/persist-research-snapshot.yml"


class ResearchSnapshotWorkflowSyntax(unittest.TestCase):
    def test_all_embedded_python_scripts_compile(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        scripts = re.findall(r"(?m)^\s{10}python - <<'PY'\n(.*?)^\s{10}PY\s*$", workflow, re.S | re.M)
        self.assertGreaterEqual(len(scripts), 3)
        for number, block in enumerate(scripts, 1):
            lines = block.splitlines()
            self.assertTrue(all(not line.strip() or line.startswith("          ") for line in lines))
            source = "\n".join(line[10:] for line in lines)
            with self.subTest(script=number):
                ast.parse(source, filename=f"workflow-python-{number}")


if __name__ == "__main__":
    unittest.main()
