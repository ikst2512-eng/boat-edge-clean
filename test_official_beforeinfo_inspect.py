import unittest
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from official_prerace_capture import capture_beforeinfo, save_raw_receipt, JST
from official_beforeinfo_inspect import inspect_beforeinfo_html, inspect_saved_beforeinfo

RECEIPT={"race_key":"20261027-22-05","status":"raw_html_only","verified_preview":False}

class InspectionTests(unittest.TestCase):
    def test_complete_headings_never_verify_values(self):
        html="<html><body><table><tr><th>展示タイム</th><th>チルト</th></tr></table><h2>スタート展示</h2><p>気温 風速 水温 波高</p></body></html>".encode()
        result=inspect_beforeinfo_html(RECEIPT,html)
        self.assertTrue(all(result["sections_present"].values()))
        self.assertEqual(result["status"],"inspection_only")
        self.assertFalse(result["verified_preview"])
        self.assertFalse(result["actual_entry_verified"])
        self.assertEqual(result["racers"],[])
        self.assertEqual(result["start_exhibition"],[])
    def test_incomplete_html_is_not_verified(self):
        result=inspect_beforeinfo_html(RECEIPT,"<html><body><p>展示タイム</p></body></html>".encode("utf-8"))
        self.assertIn("start_exhibition",result["missing_sections"])
        self.assertFalse(result["verified_preview"])
    def test_script_labels_are_not_evidence(self):
        result=inspect_beforeinfo_html(RECEIPT,b"<html><script>var label='\xe5\xb1\x95\xe7\xa4\xba\xe3\x82\xbf\xe3\x82\xa4\xe3\x83\xa0';</script></html>")
        self.assertFalse(result["sections_present"]["exhibition_time"])
    def test_saved_inspection_requires_complete_verified_receipt(self):
        now = datetime(2026, 10, 27, 14, 55, tzinfo=JST)
        deadline = now + timedelta(minutes=5)
        class Response:
            status=200
            headers={"Content-Type":"text/html"}
            def __enter__(self): return self
            def __exit__(self,*args): pass
            def read(self,n): return "<html><body>展示タイム スタート展示</body></html>".encode()
        receipt, raw = capture_beforeinfo("20261027-22-05", deadline, now=now, opener=lambda *args, **kwargs: Response())
        with tempfile.TemporaryDirectory() as directory:
            paths = save_raw_receipt(receipt,raw,directory,deadline=deadline)
            inspected = inspect_saved_beforeinfo(directory,receipt["race_key"],receipt["sha256"],deadline=deadline)
            self.assertEqual(inspected["status"],"inspection_only")
            self.assertFalse(inspected["verified_preview"])
            Path(paths[0]).write_bytes(b"tampered")
            with self.assertRaises(ValueError):
                inspect_saved_beforeinfo(directory,receipt["race_key"],receipt["sha256"],deadline=deadline)

    def test_reject_promotion(self):
        with self.assertRaises(ValueError):
            inspect_beforeinfo_html({**RECEIPT,"verified_preview":True},b"<html></html>")

if __name__=="__main__":
    unittest.main()
