"""Compile workflow-embedded Python before allowing PR merges."""
import ast
import textwrap
import unittest
from pathlib import Path


class InlinePythonSyntaxTests(unittest.TestCase):
    def test_joint_t12_dispatch_python_is_valid(self):
        workflow = Path(".github/workflows/official-joint-t12-dispatch.yml").read_text()
        self.assertEqual(workflow.count("python - <<'PY'"), 1)
        body = workflow.split("          python - <<'PY'\n", 1)[1].split("\n          PY", 1)[0]
        code = textwrap.dedent(body)
        ast.parse(code, filename="official-joint-t12-dispatch.yml:embedded-python")
        self.assertIn("failure['failure_category']=classify(", code)
        self.assertIn("print('BEFORE_FAILED'", code)


if __name__ == "__main__":
    unittest.main()
