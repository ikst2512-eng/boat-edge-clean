import unittest
from scripts.inventory_four_mode_capture_runs import inventory

class InventoryTest(unittest.TestCase):
    def test_failure_step_reported_without_claiming_saved(self):
        def fetch(url):
            if "/jobs?" in url:
                return {"jobs": [{"name": "capture", "conclusion": "failure", "steps": [
                    {"name": "Capture predeadline records", "conclusion": "success"},
                    {"name": "Stage only immutable new forecasts and check receipt window", "conclusion": "failure"}]}]}
            self.assertIn("event=schedule", url)
            return {"workflow_runs": [
                {"event": "schedule", "id": 123, "created_at": "2026-11-03T00:00:00Z",
                 "status": "completed", "conclusion": "failure",
                 "html_url": "https://github.com/example/repo/actions/runs/123"}]}
        d = inventory("example/repo", "test", fetch)
        self.assertEqual(d["scheduled_run_count"], 1)
        self.assertEqual(d["runs"][0]["failed_steps"], ["Stage only immutable new forecasts and check receipt window"])
        self.assertEqual(d["runs"][0]["capture_conclusion"], "failure")
        self.assertFalse(d["v2_saved_proven"])
    def test_reject_other_event(self):
        with self.assertRaises(ValueError):
            inventory("example/repo", "test", lambda u: {"workflow_runs": [{"event": "pull_request", "id": 1}]})
    def test_reject_missing_token(self):
        with self.assertRaises(ValueError):
            inventory("example/repo", "", lambda u: {"workflow_runs": []})
    def test_reject_missing_capture_job(self):
        def fetch(url):
            if "/jobs?" in url:
                return {"jobs": [{"name": "test", "steps": []}]}
            return {"workflow_runs": [{"event": "schedule", "id": 1}]}
        with self.assertRaises(ValueError):
            inventory("example/repo", "test", fetch)
if __name__ == "__main__":
    unittest.main()
