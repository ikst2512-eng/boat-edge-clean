"""Protect V2 nightly CI from masking Python audit failure behind tee."""
import re
import subprocess
import tempfile
import unittest
from pathlib import Path


WORKFLOW = (Path(__file__).resolve().parent / ".github" / "workflows"
            / "v2-predeclared-shadow-research.yml")


class NightlyPipelineExitTests(unittest.TestCase):
    def test_every_python_tee_pipeline_is_fail_closed(self):
        lines = WORKFLOW.read_text(encoding="utf-8").splitlines()
        pipelines = 0
        for index, line in enumerate(lines):
            if "| tee " not in line or line.lstrip().startswith("#"):
                continue
            pipelines += 1
            self.assertFalse(re.search(r"^\s+run: .*\| tee ", line),
                             f"Inline unguarded pipeline at line {index + 1}")
            self.assertIn("python ", line)
            headers = [i for i in range(index)
                       if re.match(r"^\s{8}run: ", lines[i])]
            self.assertTrue(headers)
            start = headers[-1]
            self.assertEqual(lines[start].strip(), "run: |")
            commands = "\n".join(lines[start + 1:index])
            self.assertRegex(commands, r"(?m)^\s+set -o pipefail\s*$",
                             f"Missing pipefail at line {index + 1}")
        self.assertGreaterEqual(pipelines, 14)

    def test_python_failure_survives_tee_log_capture(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "diagnostic.log"
            cmd = ('set -o pipefail; python -c "import sys;'
                   'print(\'frozen audit failed\');sys.exit(2)" | tee '
                   + str(log))
            result = subprocess.run(["bash", "-c", cmd],
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 2)
            self.assertIn("frozen audit failed", log.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
