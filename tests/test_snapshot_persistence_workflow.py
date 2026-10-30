"""Guard predeadline snapshot workflow stage/commit ordering."""
import unittest
from pathlib import Path

class PersistenceWorkflowTest(unittest.TestCase):
    def test_checks_staged_file_before_commit(self):
        src = (Path(__file__).resolve().parents[1] / ".github/workflows/persist-research-snapshot.yml").read_text()
        self.assertLess(src.index('["git", "diff", "--cached", "--name-only"]'),
                        src.index('git commit -m "research: preserve predeadline snapshot and model mass"'))
        self.assertLess(src.index('git commit -m "research: preserve predeadline snapshot and model mass"'),
                        src.index("git push origin HEAD:main"))
        self.assertIn("Too late to publish before cutoff", src)

if __name__ == "__main__":
    unittest.main()
