import unittest
from scripts.audit_legacy_workflow_inventory import inventory


class WorkflowInventoryTests(unittest.TestCase):
    def test_no_deletion_permission_from_no_recent_runs(self):
        tree = {"sha": "a"*40, "tree": [
            {"type": "blob", "path": ".github/workflows/fresh-audit.yml"},
            {"type": "blob", "path": ".github/workflows/other.yml"},
            {"type": "blob", "path": "README.md"}]}
        result = inventory(tree, [{"path": ".github/workflows/other.yml",
                                    "created_at": "2026-10-29T00:00:00Z",
                                    "conclusion": "success"}])
        self.assertEqual(result["workflow_count"], 2)
        self.assertEqual(result["not_seen_in_sample_count"], 1)
        self.assertFalse(result["delete_authorized"])
        self.assertTrue(all(not w["delete_authorized"] for w in result["workflows"]))
        self.assertTrue(all(w["requires_source_dependency_inspection"]
                            for w in result["workflows"]))


if __name__ == "__main__":
    unittest.main()
