import base64
import hashlib
import json
import unittest
from github_receipt_verify import verify

class ReceiptTests(unittest.TestCase):
    def setUp(self):
        self.code = "202610281201"
        self.path = "research_prospective_pairs/" + self.code + ".json"
        self.raw = json.dumps({"race_code": self.code, "cutoff_jst": "2026-10-28T12:48:00+09:00", "status":"research_unvalidated", "prospective_verified":False, "source_snapshot_generated_at":"2026-10-28T12:20:00+09:00", "frozen_at_jst":"2026-10-28T12:30:00+09:00", "baseline_model_id":"baseline", "candidate_model_id":"candidate"}).encode()
        self.digest = hashlib.sha256(self.raw).hexdigest()
        self.blob_sha = hashlib.sha1(b"blob " + str(len(self.raw)).encode() + bytes([0]) + self.raw).hexdigest()
        self.commit = "a"*40
        self.tree_sha = "b"*40
        self.parent_sha = "c"*40
        self.parent_tree_sha = "d"*40
        self.prefix = "/repos/ikst2512-eng/boat-edge-clean"
        self.responses = {
            self.prefix + "/actions/runs/99": {"event":"push","head_sha":self.commit,
                "head_branch":"research/prospective","repository":{"full_name":"ikst2512-eng/boat-edge-clean"},
                "status":"completed","conclusion":"success","created_at":"2026-10-28T03:40:00Z"},
            self.prefix + "/git/commits/" + self.commit: {"tree":{"sha":self.tree_sha},"parents":[{"sha":self.parent_sha}]},
            self.prefix + "/git/commits/" + self.parent_sha: {"tree":{"sha":self.parent_tree_sha}},
            self.prefix + "/git/trees/" + self.parent_tree_sha + "?recursive=1": {"truncated":False,"tree":[]},
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
    def test_server_receipt_never_authorizes_scoring(self):
        result=self.check()
        self.assertFalse(result["ready_for_scoring"])
        self.assertFalse(result["outcome_access_authorized"])
        self.assertIn("independent_source_csv_receipt",result["outstanding_evidence"])
        self.assertIn("model_source_sha_attestation",result["outstanding_evidence"])
        self.assertIn("preregistration_server_receipt",result["outstanding_evidence"])
    def test_fake_supplied_blob_rejected(self):
        self.responses[self.prefix + "/git/blobs/" + self.blob_sha]["content"]=base64.b64encode(b"forged").decode()
        with self.assertRaises(ValueError):self.check()
    def test_wrong_tree_path_rejected(self):
        self.responses[self.prefix + "/git/trees/" + self.tree_sha + "?recursive=1"]["tree"]=[]
        with self.assertRaises(ValueError):self.check()
    def test_wrong_branch_rejected(self):
        self.responses[self.prefix + "/actions/runs/99"]["head_branch"]="main"
        with self.assertRaises(ValueError):self.check()
    def test_existing_parent_path_rejected(self):
        self.responses[self.prefix + "/git/trees/" + self.parent_tree_sha + "?recursive=1"]["tree"]=[{"path":self.path}]
        with self.assertRaises(ValueError):self.check()
    def test_grandparent_file_rejected(self):
        grandparent = "e"*40
        grandtree = "f"*40
        self.responses[self.prefix + "/git/commits/" + self.parent_sha]["parents"]=[{"sha":grandparent}]
        self.responses[self.prefix + "/git/commits/" + grandparent]={"tree":{"sha":grandtree},"parents":[]}
        self.responses[self.prefix + "/git/trees/" + grandtree + "?recursive=1"]={"truncated":False,"tree":[{"path":self.path,"type":"blob","sha":self.blob_sha}]}
        with self.assertRaisesRegex(ValueError,"ancestry"):
            self.check()
    def test_truncated_history_rejected(self):
        self.responses[self.prefix + "/git/trees/" + self.parent_tree_sha + "?recursive=1"]["truncated"]=True
        with self.assertRaises(ValueError):
            self.check()
    def test_root_parent_passes(self):
        result=self.check()
        self.assertTrue(result["full_history_first_add_verified"])
        self.assertEqual(result["ancestors_checked"],1)
    def test_failed_workflow_rejected(self):
        self.responses[self.prefix + "/actions/runs/99"]["conclusion"]="failure"
        with self.assertRaises(ValueError):self.check()
    def replace_pair_record(self, **updates):
        record=json.loads(self.raw)
        record.update(updates)
        self.raw=json.dumps(record).encode()
        self.digest=hashlib.sha256(self.raw).hexdigest()
        self.blob_sha=hashlib.sha1(b"blob "+str(len(self.raw)).encode()+bytes([0])+self.raw).hexdigest()
        tree=self.responses[self.prefix+"/git/trees/"+self.tree_sha+"?recursive=1"]
        tree["tree"][0]["sha"]=self.blob_sha
        self.responses[self.prefix+"/git/blobs/"+self.blob_sha]={"encoding":"base64","content":base64.b64encode(self.raw).decode()}
    def test_frozen_after_server_push_rejected(self):
        self.replace_pair_record(frozen_at_jst="2026-10-28T12:45:00+09:00")
        with self.assertRaisesRegex(ValueError,"chronology"):self.check()
    def test_post_cutoff_generation_rejected(self):
        self.replace_pair_record(source_snapshot_generated_at="2026-10-28T12:49:00+09:00")
        with self.assertRaisesRegex(ValueError,"chronology"):self.check()
    def test_unvalidated_research_pair_only(self):
        self.replace_pair_record(status="formal")
        with self.assertRaisesRegex(ValueError,"unvalidated"):self.check()
    def test_late_receipt_rejected(self):
        self.responses[self.prefix + "/actions/runs/99"]["created_at"]="2026-10-28T03:49:00Z"
        with self.assertRaises(ValueError):self.check()
    def test_wrong_run_sha_rejected(self):
        self.responses[self.prefix + "/actions/runs/99"]["head_sha"]="f"*40
        with self.assertRaises(ValueError):self.check()

if __name__=="__main__":
    unittest.main()
