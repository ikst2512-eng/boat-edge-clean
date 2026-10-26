import io
import unittest
import tempfile
from pathlib import Path
import json
from datetime import datetime, timedelta
from official_prerace_capture import capture_beforeinfo, save_raw_receipt, read_raw_receipt, JST

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
    def test_immutable_raw_archive(self):
        receipt, raw = capture_beforeinfo("20261027-04-10", self.deadline, now=self.now, opener=self.fetch)
        with tempfile.TemporaryDirectory() as directory:
            paths = save_raw_receipt(receipt, raw, directory)
            self.assertEqual(Path(paths[0]).read_bytes(), raw)
            self.assertEqual(json.loads(Path(paths[1]).read_text())["sha256"], receipt["sha256"])
            self.assertEqual(len(list(Path(directory).glob("*.complete"))), 1)
            with self.assertRaises(FileExistsError):
                save_raw_receipt(receipt, raw, directory)
            with self.assertRaises(ValueError):
                save_raw_receipt({**receipt, "unlock": True}, raw, directory)
            with self.assertRaises(ValueError):
                save_raw_receipt(receipt, b"altered", directory)
    def test_completed_receipt_read_and_tamper_rejection(self):
        receipt, raw = capture_beforeinfo("20261027-04-10", self.deadline, now=self.now, opener=self.fetch)
        with tempfile.TemporaryDirectory() as directory:
            paths = save_raw_receipt(receipt, raw, directory)
            self.assertEqual(read_raw_receipt(directory, receipt["race_key"], receipt["sha256"])[1], raw)
            marker = Path(paths[0]).with_suffix(".complete")
            marker.unlink()
            with self.assertRaises(FileNotFoundError):
                read_raw_receipt(directory, receipt["race_key"], receipt["sha256"])
            marker.write_bytes(receipt["sha256"].encode("ascii") + bytes([10]))
            Path(paths[0]).write_bytes(b"tampered")
            with self.assertRaises(ValueError):
                read_raw_receipt(directory, receipt["race_key"], receipt["sha256"])
            Path(paths[0]).write_bytes(raw)
            Path(paths[1]).write_text(json.dumps({**receipt, "source": "https://example.com"}))
            with self.assertRaises(ValueError):
                read_raw_receipt(directory, receipt["race_key"], receipt["sha256"])

    def test_wrong_race_date_and_missing_timestamp_rejected(self):
        receipt, raw = capture_beforeinfo("20261027-04-10", self.deadline, now=self.now, opener=self.fetch)
        with tempfile.TemporaryDirectory() as directory:
            paths = save_raw_receipt(receipt, raw, directory)
            for stamp in ["2026-10-26T14:55:00+09:00", "2026-10-27T14:55:00", "invalid"]:
                Path(paths[1]).write_text(json.dumps({**receipt, "fetched_at": stamp}))
                with self.assertRaises(ValueError):
                    read_raw_receipt(directory, receipt["race_key"], receipt["sha256"])
            Path(paths[1]).write_text(json.dumps({k:v for k,v in receipt.items() if k != "fetched_at"}))
            with self.assertRaises(ValueError):
                read_raw_receipt(directory, receipt["race_key"], receipt["sha256"])

    def test_lock_rejects_concurrent_writer(self):
        receipt, raw = capture_beforeinfo("20261027-04-10", self.deadline, now=self.now, opener=self.fetch)
        with tempfile.TemporaryDirectory() as directory:
            lock = Path(directory) / (receipt["race_key"] + "-" + receipt["sha256"] + ".lock")
            lock.touch()
            with self.assertRaises(FileExistsError):
                save_raw_receipt(receipt, raw, directory)
            self.assertEqual(list(Path(directory).glob("*.complete")), [])

    def test_wrong_content_type_rejected(self):
        class JsonResponse(Response):
            headers = {"Content-Type": "application/json"}
        with self.assertRaises(ValueError):
            capture_beforeinfo("20261027-04-10", self.deadline, now=self.now, opener=lambda *a, **kw: JsonResponse())

if __name__ == "__main__":
    unittest.main()
