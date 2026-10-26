import io
import unittest
from datetime import datetime, timedelta
from official_prerace_capture import capture_beforeinfo, JST

class Response:
    status = 200
    headers = {"Content-Type": "text/html; charset=utf-8"}
    def __init__(self, raw=b"<html>official</html>"):
        self.body = io.BytesIO(raw)
    def __enter__(self): return self
    def __exit__(self, *_): pass
    def read(self, n): return self.body.read(n)

class CaptureTests(unittest.TestCase):
    def setUp(self):
        self.deadline = datetime(2026, 10, 27, 15, 0, tzinfo=JST)
        self.now = self.deadline - timedelta(minutes=5)
        self.urls = []
    def fetch(self, req, timeout):
        self.urls.append(req.full_url)
        self.assertEqual(timeout, 12)
        return Response()
    def test_receipt_is_raw_only(self):
        receipt, raw = capture_beforeinfo("20261027-04-10", self.deadline, now=self.now, opener=self.fetch)
        self.assertEqual(self.urls, ["https://www.boatrace.jp/owpc/pc/race/beforeinfo?hd=20261027&jcd=04&rno=10"])
        self.assertEqual(receipt["status"], "raw_html_only")
        self.assertFalse(receipt["verified_preview"])
        self.assertFalse(receipt["actual_entry_verified"])
        self.assertFalse(receipt["results_seen"])
        self.assertFalse(receipt["unlock"])
        self.assertFalse(receipt["scoring"])
        self.assertEqual(receipt["bytes"], len(raw))
        self.assertEqual(len(receipt["sha256"]), 64)
    def test_invalid_or_late_never_fetches(self):
        for key in ["20261027-25-01", "20261027-04-13", "20260230-04-01", "20261027-04-01/../raceresult"]:
            with self.assertRaises(ValueError):
                capture_beforeinfo(key, self.deadline, now=self.now, opener=self.fetch)
        with self.assertRaises(ValueError):
            capture_beforeinfo("20261027-04-10", self.deadline, now=self.deadline-timedelta(minutes=1), opener=self.fetch)
        with self.assertRaises(ValueError):
            capture_beforeinfo("20261027-04-10", self.deadline.replace(tzinfo=None), now=self.now, opener=self.fetch)
        self.assertEqual(self.urls, [])
    def test_empty_and_oversize_rejected(self):
        for body in [b"", b"x"*1_500_001]:
            with self.assertRaises(ValueError):
                capture_beforeinfo("20261027-04-10", self.deadline, now=self.now, opener=lambda *a, **kw: Response(body))
    def test_wrong_content_type_rejected(self):
        class JsonResponse(Response):
            headers = {"Content-Type": "application/json"}
        with self.assertRaises(ValueError):
            capture_beforeinfo("20261027-04-10", self.deadline, now=self.now, opener=lambda *a, **kw: JsonResponse())

if __name__ == "__main__":
    unittest.main()
