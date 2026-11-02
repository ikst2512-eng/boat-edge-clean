import unittest
from scripts.inventory_four_mode_actions_evidence import inventory

class InventoryTests(unittest.TestCase):
    def test_metadata_never_claims_success(self):
        def fake(path, token, repo):
            if "/runs?" in path:
                return {"workflow_runs":[{"id":1,"event":"schedule","conclusion":"success","created_at":"2026-11-03T00:00:00Z"},{"id":2,"event":"pull_request","conclusion":"success"}]}
            return {"artifacts":[{"name":"four-mode-capture-1","expired":False}]}
        r=inventory("owner/repo","token",fake)
        self.assertEqual(r["eligible_runs"],1)
        self.assertTrue(r["rows"][0]["capture_artifact_present"])
        self.assertFalse(r["rows"][0]["hole_shadow_file_contents_verified"])
        self.assertFalse(r["prospective_shadow_collection_verified"])
    def test_missing_token_is_error(self):
        with self.assertRaises(ValueError):
            inventory("owner/repo","")

if __name__=="__main__":unittest.main()
