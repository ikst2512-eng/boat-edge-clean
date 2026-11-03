import unittest
from datetime import datetime, timezone
from scripts.inventory_four_mode_watchdog_dispatch import inventory

NOW = datetime(2026, 11, 3, 6, tzinfo=timezone.utc)

def row(id, event, at, conclusion="success"):
    return {"id": id, "event": event, "created_at": at,
            "status": "completed", "conclusion": conclusion,
            "html_url": f"https://github.com/example/project/actions/runs/{id}"}

class WatchdogInventoryTest(unittest.TestCase):
    def test_split_schedule_dispatch_and_watchdog(self):
        events = {
            ("four-mode-prospective-capture.yml", "schedule"): [row(1, "schedule", "2026-11-03T03:54:14Z")],
            ("four-mode-prospective-capture.yml", "workflow_dispatch"): [row(2, "workflow_dispatch", "2026-11-03T05:30:00Z")],
            ("four-mode-capture-watchdog.yml", "schedule"): [],
            ("four-mode-capture-watchdog.yml", "push"): [row(3, "push", "2026-11-03T05:25:00Z")]}
        def fetch(url, token):
            for (workflow, event), vals in events.items():
                if workflow in url and ("event=" + event) in url:
                    return {"workflow_runs": vals}
            raise AssertionError(url)
        d = inventory("example/project", "fake", fetch, NOW)
        self.assertEqual(d["capture_schedule"]["returned"], 1)
        self.assertEqual(d["capture_workflow_dispatch"]["success"], 1)
        self.assertEqual(d["watchdog_push"]["returned"], 1)
        self.assertEqual(d["minutes_since_latest_capture"], 30)
        self.assertEqual(d["latest_capture"]["id"], 2)
        self.assertFalse(d["dispatch_accepted_proven"])
        self.assertFalse(d["forecast_saved_proven"])

    def test_no_capture_is_unknown_not_zero_minutes(self):
        def fetch(url, token):
            return {"workflow_runs": []}
        d = inventory("example/project", "fake", fetch, NOW)
        self.assertIsNone(d["minutes_since_latest_capture"])
        self.assertIsNone(d["latest_capture"])

    def test_fail_closed_on_wrong_event_and_malformed_payload(self):
        def wrong(url, token):
            return {"workflow_runs": [row(1, "pull_request", "2026-11-03T01:00:00Z")]}
        with self.assertRaises(ValueError):
            inventory("example/project", "fake", wrong, NOW)
        with self.assertRaises(ValueError):
            inventory("example/project", "fake", lambda *_: {}, NOW)

    def test_reject_missing_token(self):
        with self.assertRaises(ValueError):
            inventory("example/project", "", lambda *_: {"workflow_runs": []}, NOW)

    def test_pending_not_mistaken_for_success(self):
        def fetch(url, token):
            if "four-mode-prospective-capture.yml" in url and "event=schedule" in url:
                r = row(4, "schedule", "2026-11-03T05:58:00Z", None)
                r["status"] = "in_progress"
                return {"workflow_runs": [r]}
            return {"workflow_runs": []}
        d = inventory("example/project", "fake", fetch, NOW)
        self.assertEqual(d["capture_schedule"]["pending"], 1)
        self.assertEqual(d["capture_schedule"]["success"], 0)

if __name__ == "__main__":
    unittest.main()
