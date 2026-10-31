import csv,io,tempfile,unittest
from datetime import datetime
from research_model import JST
from scripts.collect_late_preview_evidence import capture

class CaptureTest(unittest.TestCase):
    def test_live_fetch_uses_isolated_predeadline_gate(self):
        buf=io.StringIO()
        writer=csv.DictWriter(buf,fieldnames=["レースコード","締切時刻","取得日時","艇1_コース"])
        writer.writeheader()
        writer.writerow({"レースコード":"202610312312","締切時刻":"20:00","取得日時":"2026-10-31T19:53:00+09:00","艇1_コース":"1"})
        raw=buf.getvalue().encode()
        with tempfile.TemporaryDirectory() as tmp:
            report=capture("20261031",tmp,lambda url:raw,datetime(2026,10,31,19,54,tzinfo=JST))
            self.assertEqual(report["sources"]["stt"]["saved"],1)
            self.assertFalse(report["research_snapshots_modified"])
            from pathlib import Path
            self.assertFalse((Path(tmp)/"research_snapshots").exists())
    def test_late_receipt_saves_zero(self):
        buf=io.StringIO()
        writer=csv.DictWriter(buf,fieldnames=["レースコード","締切時刻","取得日時"])
        writer.writeheader()
        writer.writerow({"レースコード":"202610312312","締切時刻":"20:00","取得日時":"2026-10-31T19:53:00+09:00"})
        with tempfile.TemporaryDirectory() as tmp:
            result=capture("20261031",tmp,lambda url:buf.getvalue().encode(),datetime(2026,10,31,19,59,tzinfo=JST))
            self.assertEqual(sum(x["saved"] for x in result["sources"].values()),0)
if __name__=="__main__": unittest.main()
