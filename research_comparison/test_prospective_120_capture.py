import json
import hashlib
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from prospective_120_capture import JST, freeze

class ProspectiveCaptureTests(unittest.TestCase):
    def kwargs(self):
        now=datetime.now(JST)
        date=(now+timedelta(days=1)).strftime("%Y%m%d")
        return dict(race_code=date+"1201",rates=[5.0]*6,
                    model_sha="a"*40,
                    input_sha256=hashlib.sha256((
                        hashlib.sha256(b"title csv").hexdigest()+":"+
                        hashlib.sha256(b"cards csv").hexdigest()).encode("ascii")).hexdigest(),
                    title_bytes=b"title csv",cards_bytes=b"cards csv",
                    source_received_at=(now-timedelta(seconds=5)).isoformat(),
                    cutoff_jst=(now+timedelta(days=1)).isoformat())
    def test_exclusive_capture_and_complete_probabilities(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"record.json"
            meta=freeze(path,**self.kwargs())
            record=json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(meta["tickets"],120)
            self.assertEqual(len(record["probabilities"]),120)
            self.assertAlmostEqual(sum(record["probabilities"].values()),1)
            self.assertFalse(record["validated"])
            self.assertIn("NOT_INDEPENDENTLY_VERIFIED",meta["status"])
            with self.assertRaises(FileExistsError):
                freeze(path,**self.kwargs())
    def test_reject_expired_cutoff(self):
        kwargs=self.kwargs()
        now=datetime.now(JST)
        kwargs["race_code"]=now.strftime("%Y%m%d")+"1201"
        kwargs["cutoff_jst"]=(now-timedelta(seconds=1)).isoformat()
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                freeze(Path(d)/"none.json",**kwargs)
    def test_reject_invalid_race_identity(self):
        for code in ("202602301201","202610272501","202610271213","202610270001"):
            kwargs=self.kwargs()
            kwargs["race_code"]=code
            with tempfile.TemporaryDirectory() as d:
                with self.subTest(code=code), self.assertRaises(ValueError):
                    freeze(Path(d)/"none.json",**kwargs)
    def test_reject_digest_not_backed_by_original_bytes(self):
        kwargs=self.kwargs()
        kwargs["input_sha256"]="b"*64
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError,"input bytes do not match"):
                freeze(Path(d)/"none.json",**kwargs)
    def test_source_order_matters(self):
        kwargs=self.kwargs()
        kwargs["title_bytes"],kwargs["cards_bytes"]=kwargs["cards_bytes"],kwargs["title_bytes"]
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError,"composite input SHA256"):
                freeze(Path(d)/"none.json",**kwargs)
    def test_reject_late_source(self):
        kwargs=self.kwargs()
        kwargs["source_received_at"]=(datetime.now(JST)+timedelta(hours=1)).isoformat()
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                freeze(Path(d)/"none.json",**kwargs)
if __name__=="__main__":
    unittest.main()
