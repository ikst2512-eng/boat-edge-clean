import unittest
from scripts.inventory_four_mode_actions_evidence import inventory

class InventoryTests(unittest.TestCase):
    def test_metadata_never_claims_success(self):
        def fake(path, token, repo):
            if "event=schedule" in path:
                return {"workflow_runs":[{"id":1,"event":"schedule","conclusion":"success","created_at":"2026-11-03T00:00:00Z"}]}
            if "event=workflow_dispatch" in path:
                return {"workflow_runs":[]}
            return {"artifacts":[{"name":"four-mode-capture-1","expired":False}]}
        r=inventory("owner/repo","token",fake)
        self.assertEqual(r["eligible_runs"],1)
        self.assertTrue(r["rows"][0]["capture_artifact_present"])
        self.assertFalse(r["rows"][0]["hole_shadow_file_contents_verified"])
        self.assertFalse(r["prospective_shadow_collection_verified"])
    def test_event_filters_do_not_crowd_out_schedule(self):
        queries=[]
        def fake(path, token, repo):
            queries.append(path)
            if "event=schedule" in path:
                return {"workflow_runs":[{"id":22,"event":"schedule","conclusion":"failure","created_at":"2026-11-03T01:00:00Z"}]}
            if "event=workflow_dispatch" in path:
                return {"workflow_runs":[{"id":21,"event":"workflow_dispatch","conclusion":"success","created_at":"2026-11-02T23:00:00Z"}]}
            return {"artifacts":[]}
        result=inventory("owner/repo","token",fake,limit=5)
        self.assertEqual([r["run_id"] for r in result["rows"]],[22,21])
        self.assertTrue(any("event=schedule&per_page=5" in q for q in queries))
        self.assertTrue(any("event=workflow_dispatch&per_page=5" in q for q in queries))
        self.assertFalse(result["prospective_shadow_collection_verified"])

    def test_missing_token_is_error(self):
        with self.assertRaises(ValueError):
            inventory("owner/repo","")

if __name__=="__main__":unittest.main()
