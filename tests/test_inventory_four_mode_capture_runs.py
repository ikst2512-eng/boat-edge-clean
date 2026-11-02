import unittest
from scripts.inventory_four_mode_capture_runs import inventory

class InventoryTest(unittest.TestCase):
    def test_scheduled_runs_only(self):
        def fetch(url):
            self.assertIn("event=schedule", url)
            return {"workflow_runs": [
                {"event": "schedule", "id": 123, "created_at": "2026-11-03T00:00:00Z",
                 "status": "completed", "conclusion": "failure",
                 "html_url": "https://github.com/example/repo/actions/runs/123"}]}
        d = inventory("example/repo", "test", fetch)
        self.assertEqual(d["scheduled_run_count"], 1)
        self.assertFalse(d["v2_saved_proven"])
    def test_reject_other_event(self):
        with self.assertRaises(ValueError):
            inventory("example/repo", "test", lambda u: {"workflow_runs": [{"event": "pull_request", "id": 1}]})
    def test_reject_missing_token(self):
        with self.assertRaises(ValueError):
            inventory("example/repo", "", lambda u: {"workflow_runs": []})
if __name__ == "__main__":
    unittest.main()
