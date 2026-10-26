import hashlib
import unittest
from datetime import datetime, timedelta
from paired_compare import TICKETS
from snapshot_bridge import draft

class SnapshotBridgeTests(unittest.TestCase):
    def record(self):
        tickets = sorted(TICKETS)
        rates = {k: 1/120 for k in tickets}
        a = hashlib.sha256(b"title").hexdigest()
        c = hashlib.sha256(b"cards").hexdigest()
        digest = hashlib.sha256((a+":"+c).encode("ascii")).hexdigest()
        return dict(status="research",validated=False,race_code="202610281201",
                    input_hash_scope="source_csv_byte_hashes_ordered_title_cards",
                    source_title_sha256=a,source_cards_sha256=c,input_sha256=digest,
                    model_id="national-beta0.4-exploratory-v1",model_sha="a"*40,
                    probabilities=rates,predictions=tickets[:10],
                    generated_at="2026-10-28T11:00:00+09:00",
                    source_received_at="2026-10-28T10:59:00+09:00",
                    cutoff_jst="2026-10-28T11:50:00+09:00")
    def test_unverified_draft(self):
        obj=draft(self.record(),filename_sha256="b"*64)
        self.assertEqual(obj["race_key"],"20261028-12-1")
        self.assertFalse(obj["ready_for_scoring"])
        self.assertFalse(obj["forecast_draft"]["independently_verified"])
        self.assertNotIn("result",obj)
        self.assertEqual(len(obj["forecast_draft"]["probabilities"]),120)
    def test_tampered_digest_rejected(self):
        d=self.record()
        d["source_cards_sha256"]="f"*64
        with self.assertRaisesRegex(ValueError,"chain mismatch"):
            draft(d,filename_sha256="b"*64)
    def test_top10_mismatch_rejected(self):
        d=self.record()
        d["predictions"]=list(reversed(d["predictions"]))
        with self.assertRaisesRegex(ValueError,"top10 differs"):
            draft(d,filename_sha256="b"*64)
    def test_missing_distribution_rejected(self):
        d=self.record()
        del d["probabilities"]
        with self.assertRaisesRegex(ValueError,"120-ticket"):
            draft(d,filename_sha256="b"*64)

if __name__=="__main__":
    unittest.main()
