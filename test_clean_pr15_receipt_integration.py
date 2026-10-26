"""End-to-end offline receipt archive readback using pinned PR15 code."""
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from hashlib import sha256
from official_prerace_capture import capture_beforeinfo, save_raw_receipt, read_raw_receipt, JST
from clean_verified_receipt_bridge import bridge_saved_official_receipt

KEY="20261027-04-10"
DEADLINE=datetime(2026,10,27,15,0,tzinfo=JST)
CAPTURED=DEADLINE-timedelta(minutes=5)
RAW=b"<html><body>offline official research fixture</body></html>"

class FakeResponse:
    status=200
    headers={"Content-Type":"text/html"}
    def __enter__(self): return self
    def __exit__(self,*args): return False
    def geturl(self): return "https://www.boatrace.jp/owpc/pc/race/beforeinfo?hd=20261027&jcd=04&rno=10"
    def read(self,n): return RAW

class PinnedPR15IntegrationTests(unittest.TestCase):
    def prepare(self, directory):
        receipt, raw = capture_beforeinfo(
            KEY, DEADLINE, now=CAPTURED, completed_at=CAPTURED,
            opener=lambda request, timeout: FakeResponse())
        save_raw_receipt(receipt,raw,directory,deadline=DEADLINE)
        racers=[{"lane":i,"registration":f"{4000+i}"} for i in range(1,7)]
        racelist={"race_key":KEY,"status":"html_candidates_unverified",
                  "official_provenance_verified":False,"racers":racers}
        parser={"race_key":KEY,"status":"research_unverified",
                "verified_preview":False,"actual_entry_verified":False,
                "raw_sha256":receipt["sha256"],"captured_at":receipt["fetched_at"],
                "start_exhibition":[{"boat_number":i,"exhibition_course":i,"exhibition_st":0.12}
                                    for i in range(1,7)]}
        return receipt,racelist,parser
    def test_real_pr15_archive_roundtrip(self):
        with tempfile.TemporaryDirectory() as directory:
            receipt,racelist,parsed=self.prepare(directory)
            result=bridge_saved_official_receipt(racelist,parsed,directory=directory,
                                                 deadline=DEADLINE,read_raw_receipt=read_raw_receipt)
            self.assertEqual(result["status"],"bridged_unverified")
            self.assertEqual(result["source_sha256"],receipt["sha256"])
            self.assertFalse(result["verified_preview"])
    def test_tampered_archive_rejected_by_pr15_reader(self):
        with tempfile.TemporaryDirectory() as directory:
            receipt,racelist,parsed=self.prepare(directory)
            stem=KEY+"-"+receipt["sha256"]
            (Path(directory)/(stem+".html")).write_bytes(b"modified source")
            with self.assertRaises(ValueError):
                bridge_saved_official_receipt(racelist,parsed,directory=directory,
                                              deadline=DEADLINE,read_raw_receipt=read_raw_receipt)

if __name__=="__main__": unittest.main()
