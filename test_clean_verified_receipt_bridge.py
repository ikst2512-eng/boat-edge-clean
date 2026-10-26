import unittest
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from clean_verified_receipt_bridge import bridge_saved_official_receipt

JST=timezone(timedelta(hours=9))
AT=datetime(2026,10,26,14,0,tzinfo=JST)
RAW=b"offline fixture"
DIGEST=sha256(RAW).hexdigest()
RACE={"race_key":"20261026-21-01","status":"html_candidates_unverified",
      "official_provenance_verified":False,
      "racers":[{"lane":i,"registration":str(4000+i)} for i in range(1,7)]}
PARSED={"race_key":RACE["race_key"],"status":"research_unverified",
        "verified_preview":False,"actual_entry_verified":False,
        "raw_sha256":DIGEST,"captured_at":AT.isoformat(),
        "start_exhibition":[{"boat_number":i,"exhibition_course":i,"exhibition_st":0.12} for i in range(1,7)]}
RECEIPT={"status":"raw_html_only","race_key":RACE["race_key"],
         "sha256":DIGEST,"bytes":len(RAW),"fetched_at":AT.isoformat(),
         "verified_preview":False,"actual_entry_verified":False,
         "results_seen":False,"unlock":False,"scoring":False}

class SavedReceiptBridgeTests(unittest.TestCase):
    def run_bridge(self, reader):
        return bridge_saved_official_receipt(
            RACE,PARSED,directory="fixture",deadline=AT+timedelta(minutes=15),
            read_raw_receipt=reader)
    def test_validated_readback_research_only(self):
        result=self.run_bridge(lambda d,k,h,deadline:(dict(RECEIPT),RAW))
        self.assertEqual(result["status"],"bridged_unverified")
        self.assertFalse(result["verified_preview"])
    def test_altered_bytes_rejected(self):
        with self.assertRaises(ValueError):
            self.run_bridge(lambda d,k,h,deadline:(dict(RECEIPT),b"modified bytes"))
    def test_wrong_length_rejected(self):
        with self.assertRaises(ValueError):
            self.run_bridge(lambda d,k,h,deadline:({**RECEIPT,"bytes":12345},RAW))
    def test_readback_error_propagates(self):
        def bad(*args,**kwargs): raise ValueError("invalid marker")
        with self.assertRaises(ValueError):
            self.run_bridge(bad)
    def test_unsafe_receipt_rejected(self):
        with self.assertRaises(ValueError):
            self.run_bridge(lambda d,k,h,deadline:({**RECEIPT,"scoring":True},RAW))

if __name__=="__main__": unittest.main()
