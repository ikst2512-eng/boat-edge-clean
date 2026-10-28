import unittest
from scripts.audit_legacy_action_references import audit

class ReferencesTest(unittest.TestCase):
    def test_no_delete_when_unreferenced(self):
        tree = {"sha": "a"*40, "tree": [
            {"type": "blob", "path": ".github/workflows/a.yml", "sha": "b"*40},
            {"type": "blob", "path": ".github/workflows/b.yml", "sha": "c"*40}]}
        bodies = {"a.yml": "on:\\n  workflow_dispatch:\\n", "b.yml": "uses: ./.github/workflows/a.yml"}
        result = audit(tree, lambda path, sha: bodies[path.split("/")[-1]])
        self.assertEqual(result["count"], 2)
        self.assertEqual(result["referenced_count"], 1)
        self.assertFalse(result["delete_authorized"])
        self.assertFalse(result["records"][1]["deletion_authorized"])

if __name__ == "__main__":
    unittest.main()
