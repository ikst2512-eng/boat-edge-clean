import unittest
from scripts.inventory_joint_t12_history import inventory, WORKFLOW


class HistoryInventoryTests(unittest.TestCase):
    def test_only_real_dispatch_and_matching_artifact_counts(self):
        urls = []
        def fetch(url):
            urls.append(url)
            if "/artifacts?" in url:
                run_id = int(url.split("/runs/")[1].split("/")[0])
                return {"artifacts": [{"id": 99, "name": "official-joint-"+str(run_id), "expired": False},
                                      {"id": 88, "name": "other", "expired": False}]}
            return {"workflow_runs": [{"id": 123, "event": "workflow_dispatch",
                                       "status": "completed", "conclusion": "success"}]}
        report = inventory("test/repo", "token", fetch)
        self.assertEqual(report["real_dispatch_runs_seen"], 1)
        self.assertEqual(report["runs_with_matching_unexpired_artifacts"], 1)
        self.assertEqual(report["runs"][0]["matching_unexpired_artifact_ids"], [99])
        self.assertIsNone(report["historical_success_rate"])
        self.assertIsNone(report["t12_complete_pairs_verified"])
        self.assertIn("event=workflow_dispatch", urls[0])

    def test_pr_runs_are_never_inventoried(self):
        def fetch(url):
            return {"workflow_runs": [{"id": 55, "event": "pull_request"}]}
        with self.assertRaises(ValueError):
            inventory("test/repo", "token", fetch)

    def test_missing_token_or_incomplete_api_fails_closed(self):
        with self.assertRaises(ValueError):
            inventory("test/repo", "", lambda _: {})
        with self.assertRaises(ValueError):
            inventory("test/repo", "token", lambda _: {"unexpected": []})

    def test_zero_runs_is_not_zero_success_rate(self):
        report = inventory("test/repo", "token", lambda _: {"workflow_runs": []})
        self.assertEqual(report["real_dispatch_runs_seen"], 0)
        self.assertIsNone(report["historical_success_rate"])


if __name__ == "__main__":
    unittest.main()
