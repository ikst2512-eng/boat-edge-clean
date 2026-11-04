import unittest
from urllib.error import HTTPError
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
    def test_http403_retains_metadata_without_inventing_capture_success(self):
        def fetch(url):
            if "/jobs?" in url:
                raise HTTPError(url, 403, "Forbidden", {}, None)
            return {"workflow_runs": [{
                "event": "schedule", "id": 17,
                "created_at": "2026-11-04T02:05:00Z",
                "status": "completed", "conclusion": "success",
                "html_url": "https://github.com/example/repo/actions/runs/17"}]}
        result = inventory("example/repo", "test", fetch)
        self.assertEqual(result["scheduled_run_count"], 1)
        self.assertFalse(result["job_details_complete"])
        self.assertEqual(result["job_details_unavailable"], [
            {"run_id": 17, "http_status": 403}])
        row = result["runs"][0]
        self.assertEqual(row["conclusion"], "success")
        self.assertIsNone(row["capture_conclusion"])
        self.assertIsNone(row["failed_steps"])
        self.assertEqual(row["job_details_status"], "http_unavailable")
        self.assertFalse(result["v2_saved_proven"])
        self.assertFalse(result["model_accuracy_proven"])

    def test_http429_partial_coverage_keeps_other_capture_details(self):
        def fetch(url):
            if "/runs/17/jobs?" in url:
                raise HTTPError(url, 429, "Too Many Requests", {}, None)
            if "/jobs?" in url:
                return {"jobs": [{"name": "capture", "conclusion": "failure",
                                  "steps": [{"name": "Freeze source",
                                             "conclusion": "failure"}]}]}
            return {"workflow_runs": [
                {"event": "schedule", "id": 17},
                {"event": "schedule", "id": 18}]}
        result = inventory("example/repo", "test", fetch)
        self.assertEqual(result["scheduled_run_count"], 2)
        self.assertEqual(result["runs"][1]["failed_steps"], ["Freeze source"])
        self.assertEqual(result["runs"][1]["job_details_status"], "verified")
        self.assertEqual(result["job_details_unavailable"], [
            {"run_id": 17, "http_status": 429}])
        self.assertFalse(result["job_details_complete"])

    def test_unexpected_job_api_error_is_not_suppressed(self):
        def fetch(url):
            if "/jobs?" in url:
                raise HTTPError(url, 500, "Server Error", {}, None)
            return {"workflow_runs": [{"event": "schedule", "id": 17}]}
        with self.assertRaises(HTTPError):
            inventory("example/repo", "test", fetch)

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
