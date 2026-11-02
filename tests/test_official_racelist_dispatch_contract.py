import unittest
from pathlib import Path


class OfficialRacelistDispatchContract(unittest.TestCase):
    def test_manual_capture_is_read_only_and_not_prediction_enabled(self):
        workflow = Path(".github/workflows/official-racelist-live-dispatch.yml").read_text()
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("contents: read", workflow)
        self.assertIn('code[:8] != datetime.now(JST).strftime("%Y%m%d")', workflow)
        self.assertIn('capture(code, "evidence"', workflow)
        self.assertIn("actions/upload-artifact@v4", workflow)
        self.assertIn("retention-days: 14", workflow)
        self.assertNotIn("git push", workflow)
        self.assertNotIn("forecast_usable: true", workflow)


if __name__ == "__main__":
    unittest.main()
