import unittest
from scripts.render_joint_t12_inventory_summary import format_summary


class T12InventorySummaryTests(unittest.TestCase):
    def test_counts_are_metadata_only(self):
        text = format_summary({
            "real_dispatch_runs_seen": 4,
            "runs_with_matching_unexpired_artifacts": 2,
            "pagination_may_be_truncated": False})
        self.assertIn("| Manual dispatch runs observed | 4 |", text)
        self.assertIn("| Runs with unexpired matching artifact | 2 |", text)
        self.assertIn("not evaluated", text)

    def test_missing_or_untrusted_metadata_rejected(self):
        for item in ({}, {"real_dispatch_runs_seen": True, "runs_with_matching_unexpired_artifacts": 1,
                           "pagination_may_be_truncated": False},
                     {"real_dispatch_runs_seen": 0, "runs_with_matching_unexpired_artifacts": 1,
                      "pagination_may_be_truncated": False}):
            with self.assertRaises(ValueError):
                format_summary(item)


if __name__ == "__main__":
    unittest.main()
