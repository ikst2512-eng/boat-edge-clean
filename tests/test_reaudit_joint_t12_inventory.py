import unittest
from scripts.reaudit_joint_t12_inventory import reaudit_inventory


class InventoryReauditTests(unittest.TestCase):
    def test_only_verified_source_pairs_count(self):
        data = {"repo":"test/repo","pagination_may_be_truncated":False,
                "real_dispatch_runs_seen":1,
                "runs":[{"run_id":123,"matching_unexpired_artifact_ids":[77,78]}]}
        def loader(repo, token, artifact):
            if artifact == 78:
                raise OSError("expired")
            return b"zip"
        result = reaudit_inventory(data, "test/repo", "token", loader,
                                  lambda raw, run: {"independently_verified_complete_pairs":2,
                                                    "attempt_reports":3})
        self.assertEqual(result["verified_complete_pair_attempts_in_inspected_artifacts"],2)
        self.assertEqual(result["status_counts"],
                         {"source_reaudit_complete":1,"source_reaudit_unresolved":1})
        self.assertIsNone(result["historical_success_rate"])
        self.assertFalse(result["full_history_verified"])

    def test_truncated_inventory_rejected(self):
        with self.assertRaises(ValueError):
            reaudit_inventory({"repo":"test/repo","pagination_may_be_truncated":True,
                               "real_dispatch_runs_seen":0,"runs":[]},
                              "test/repo","token",lambda *a: b"",lambda *a: {})

    def test_duplicate_run_rejected(self):
        data = {"repo":"test/repo","pagination_may_be_truncated":False,
                "real_dispatch_runs_seen":2,
                "runs":[{"run_id":123,"matching_unexpired_artifact_ids":[]}] * 2}
        with self.assertRaises(ValueError):
            reaudit_inventory(data,"test/repo","token",lambda *a: b"",lambda *a: {})


if __name__ == "__main__":
    unittest.main()
