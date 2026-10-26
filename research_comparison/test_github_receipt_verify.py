import base64
import hashlib
import json
import unittest
from github_receipt_verify import verify

class ReceiptTests(unittest.TestCase):
    def setUp(self):
        self.code = "202610281201"
        self.path = "research_prospective_pairs/" + self.code + ".json"
        self.raw = json.dumps({"race_code": self.code, "cutoff_jst": "2026-10-28T12:48:00+09:00"}).encode()
        self.digest = hashlib.sha256(self.raw).hexdigest()
        self.blob_sha = hashlib.sha1(b"blob " + str(len(self.raw)).encode() + bytes([0]) + self.raw).hexdigest()
        self.commit = "a"*40
        self.tree_sha = "b"*40
        self.prefix = "/repos/ikst2512-eng/boat-edge-clean"
        self.responses = {
            self.prefix + "/actions/runs/99": {"event":"push","head_sha":self.commit,
                "head_branch":"research/prospective","repository":{"full_name":"ikst2512-eng/boat-edge-clean"},
                "status":"completed","created_at":"2026-10-28T03:40:00Z"},
            self.prefix + "/git/commits/" + self.commit: {"tree":{"sha":self.tree_sha}},
            self.prefix + "/git/trees/" + self.tree_sha + "?recursive=1":
                {"truncated":False,"tree":[{"path":self.path,"type":"blob","sha":self.blob_sha}]},
            self.prefix + "/git/blobs/" + self.blob_sha:
                {"encoding":"base64","content":base64.b64encode(self.raw).decode()}
        }
    def check(self):
        return verify(lambda p:self.responses[p],repo="ikst2512-eng/boat-edge-clean",
            branch="research/prospective",commit=self.commit,path=self.path,
            expected_sha256=self.digest,official_deadline="2026-10-28T13:00:00+09:00",run_id=99)
    def test_matching_commit_blob(self):
        result=self.check()
        self.assertEqual(result["status"],"SERVER_PUSH_AND_COMMIT_BLOB_MATCH")
        self.assertFalse(result["formal_validated"])
    def test_fake_supplied_blob_rejected(self):
        self.responses[self.prefix + "/git/blobs/" + self.blob_sha]["content"]=base64.b64encode(b"forged").decode()
        with self.assertRaises(ValueError):self.check()
    def test_wrong_tree_path_rejected(self):
        self.responses[self.prefix + "/git/trees/" + self.tree_sha + "?recursive=1"]["tree"]=[]
        with self.assertRaises(ValueError):self.check()
    def test_wrong_branch_rejected(self):
        self.responses[self.prefix + "/actions/runs/99"]["head_branch"]="main"
        with self.assertRaises(ValueError):self.check()
    def test_late_receipt_rejected(self):
        self.responses[self.prefix + "/actions/runs/99"]["created_at"]="2026-10-28T03:49:00Z"
        with self.assertRaises(ValueError):self.check()
    def test_wrong_run_sha_rejected(self):
        self.responses[self.prefix + "/actions/runs/99"]["head_sha"]="f"*40
        with self.assertRaises(ValueError):self.check()

if __name__=="__main__":
    unittest.main()
