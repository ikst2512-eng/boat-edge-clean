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
        target=now+timedelta(days=1)
        date=target.strftime("%Y%m%d")
        cutoff=target.replace(hour=12,minute=0,second=0,microsecond=0)
        title=("レースコード,電話投票締切予定\\n"+date+"1201,12:12\\n").encode("utf-8")
        cards=("レースコード,"+",".join(f"艇{i}_全国勝率" for i in range(1,7))+
               "\\n"+date+"1201,"+",".join(["5.0"]*6)+"\\n").encode("utf-8")
        digest=hashlib.sha256((hashlib.sha256(title).hexdigest()+":"+
                               hashlib.sha256(cards).hexdigest()).encode("ascii")).hexdigest()
        return dict(race_code=date+"1201",rates=[5.0]*6,
                    model_sha="a"*40,input_sha256=digest,
                    title_bytes=title,cards_bytes=cards,
                    source_received_at=(now-timedelta(seconds=5)).isoformat(),
                    cutoff_jst=cutoff.isoformat())
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
            with self.assertRaisesRegex(ValueError,"composite input SHA256"):
                freeze(Path(d)/"none.json",**kwargs)
    def test_source_order_matters(self):
        kwargs=self.kwargs()
        kwargs["title_bytes"],kwargs["cards_bytes"]=kwargs["cards_bytes"],kwargs["title_bytes"]
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError,"composite input SHA256"):
                freeze(Path(d)/"none.json",**kwargs)
    def test_reject_rates_not_derived_from_csv(self):
        kwargs=self.kwargs()
        kwargs["rates"]=[6.0]*6
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError,"rates differ"):
                freeze(Path(d)/"none.json",**kwargs)
    def test_reject_untrusted_cutoff(self):
        kwargs=self.kwargs()
        kwargs["cutoff_jst"]=(datetime.fromisoformat(kwargs["cutoff_jst"])+timedelta(minutes=1)).isoformat()
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError,"cutoff differs"):
                freeze(Path(d)/"none.json",**kwargs)
    def test_reject_late_source(self):
        kwargs=self.kwargs()
        kwargs["source_received_at"]=(datetime.now(JST)+timedelta(hours=1)).isoformat()
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                freeze(Path(d)/"none.json",**kwargs)
if __name__=="__main__":
    unittest.main()
