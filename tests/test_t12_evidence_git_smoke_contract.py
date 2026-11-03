import unittest
from pathlib import Path


class OneTimeEvidenceSmokeContractTests(unittest.TestCase):
    def test_one_day_only_and_no_scheduled_fallback_claim(self):
        workflow = Path(".github/workflows/t12-evidence-git-smoke-20261103.yml").read_text()
        self.assertIn("20261103", workflow)
        self.assertIn("push:", workflow)
        self.assertIn("branches: [main]", workflow)
        self.assertNotIn("\n  schedule:", workflow)
        self.assertIn("contents: write", workflow)
        self.assertIn("202611030112", workflow)
        self.assertIn("2026,11,3,20,19", workflow)
        self.assertIn('GITHUB_EVIDENCE_TOKEN: ${{ github.token }}', workflow)
        self.assertIn("--branch research-t12-external-evidence", workflow)
        self.assertIn("This is NOT an external Render Cron", workflow)


if __name__ == "__main__":
    unittest.main()
