import json
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
                    model_sha="a"*40,input_sha256="b"*64,
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
    def test_reject_late_source(self):
        kwargs=self.kwargs()
        kwargs["source_received_at"]=(datetime.now(JST)+timedelta(hours=1)).isoformat()
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                freeze(Path(d)/"none.json",**kwargs)
if __name__=="__main__":
    unittest.main()
