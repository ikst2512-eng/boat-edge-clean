import unittest
from unittest.mock import patch
from github_live_receipt import audit_live, fetch_github

class LiveReceiptTests(unittest.TestCase):
    def test_refuses_unrelated_api_routes(self):
        for route in ("/repos/ikst2512-eng/boat-edge/commits/main",
                      "/repos/ikst2512-eng/boat-edge-clean/actions/runs",
                      "/repos/ikst2512-eng/boat-edge-clean/results/latest"):
            with self.assertRaises(ValueError):
                fetch_github(route)
    def test_rejects_api_path_suffix_injection(self):
        bad=(
            "/repos/ikst2512-eng/boat-edge-clean/git/blobs/"+"a"*40+"/extra",
            "/repos/ikst2512-eng/boat-edge-clean/git/commits/"+"a"*40+"?ref=main",
            "/repos/ikst2512-eng/boat-edge-clean/git/trees/"+"a"*40+"?recursive=0",
            "/repos/ikst2512-eng/boat-edge-clean/actions/runs/99/attempts",
        )
        for route in bad:
            with self.subTest(route=route),self.assertRaises(ValueError):
                fetch_github(route)
    def test_live_audit_never_allows_scoring(self):
        with patch("github_live_receipt.verify",return_value={"ready_for_scoring":False,"status":"SERVER_PUSH_AND_COMMIT_BLOB_MATCH"}):
            report=audit_live(branch="research/paired",commit="a"*40,path="research_prospective_pairs/202610281201.json",
                              expected_sha256="b"*64,official_deadline="2026-10-28T13:00:00+09:00",run_id=99)
            self.assertFalse(report["ready_for_scoring"])
    def test_rejects_unsafe_report(self):
        with patch("github_live_receipt.verify",return_value={"ready_for_scoring":True}):
            with self.assertRaises(ValueError):
                audit_live(branch="research/paired",commit="a"*40,path="research_prospective_pairs/202610281201.json",
                           expected_sha256="b"*64,official_deadline="2026-10-28T13:00:00+09:00",run_id=99)
if __name__=="__main__":
    unittest.main()
