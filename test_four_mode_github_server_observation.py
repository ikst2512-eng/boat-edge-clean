import base64
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from four_mode_github_server_observation import observe

CODE="202611040101"
SHA="a"*40
PATH="four_mode_forecasts/"+CODE+".json"
RAW=json.dumps({"schema":"CLEAN_FOUR_MODES_PREDEADLINE_V1",
                "race_code":CODE,
                "deadline_jst":"2026-11-04T12:00:00+09:00"}).encode()
BLOB=hashlib.sha1(b"blob "+str(len(RAW)).encode()+b"\0"+RAW).hexdigest()

class RemoteObservationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        p=self.root/PATH;p.parent.mkdir();p.write_bytes(RAW)
        self.publication={"outcome":"pushed_to_main",
                          "commit_sha":SHA,"added_forecasts":1}
    def git(self,*args):
        if args[0]=="diff-tree":return (PATH+"\n").encode()
        if args[0]=="show":return RAW
        raise AssertionError(args)
    def response(self,date,payload=None):
        body=payload or {"path":PATH,"type":"file","encoding":"base64",
                         "sha":BLOB,"content":base64.b64encode(RAW).decode()}
        return lambda path:(date,json.dumps(body).encode())
    def call(self,request,publication=None):
        return observe(self.root,publication or self.publication,
                       "ikst2512-eng/boat-edge-clean",request,self.git)

    def test_server_observed_before_cutoff_but_not_first_receipt(self):
        r=self.call(self.response("Wed, 04 Nov 2026 02:30:00 GMT"))
        self.assertEqual(r["observed_before_t_minus_12"],1)
        self.assertEqual(r["records"][0]["status"],
                         "github_server_observed_before_t_minus_12")
        self.assertFalse(r["independent_first_remote_receipt_verified"])
        self.assertFalse(r["formal"])

    def test_server_observed_after_cutoff_is_not_earlier_proof(self):
        r=self.call(self.response("Wed, 04 Nov 2026 02:48:00 GMT"))
        self.assertEqual(r["observed_after_t_minus_12"],1)
        self.assertEqual(r["observed_before_t_minus_12"],0)

    def test_mismatched_remote_blob_is_unverified(self):
        payload={"path":PATH,"type":"file","encoding":"base64","sha":BLOB,
                 "content":base64.b64encode(b"bad").decode()}
        r=self.call(self.response("Wed, 04 Nov 2026 02:00:00 GMT",payload))
        self.assertEqual(r["unverified_count"],1)
        self.assertNotIn("first_add_blob_matches_remote",r["records"][0])

    def test_missing_server_date_is_unverified(self):
        r=self.call(lambda path:(None,b"{}"))
        self.assertEqual(r["unverified_count"],1)

    def test_malformed_or_missing_push_never_requests_api(self):
        self.assertEqual(self.call(lambda _:self.fail("unexpected request"),
            {"outcome":"no_eligible_candidates"})["records"],[])
        with self.assertRaisesRegex(ValueError,"invalid_publication_identity"):
            self.call(lambda _:None,{"outcome":"pushed_to_main",
                  "commit_sha":"bad","added_forecasts":1})

    def test_changed_local_blob_is_unverified(self):
        (self.root/PATH).write_bytes(b"tampered")
        r=self.call(lambda _:self.fail("must not request remote"))
        self.assertEqual(r["unverified_count"],1)

    def test_duplicate_additions_fail_closed(self):
        with self.assertRaisesRegex(ValueError,"invalid_first_add_roster"):
            observe(self.root,self.publication,"ikst2512-eng/boat-edge-clean",
                self.response("Wed, 04 Nov 2026 02:00:00 GMT"),
                lambda *args: (PATH+"\n"+PATH+"\n").encode())

if __name__=="__main__":
    unittest.main()
