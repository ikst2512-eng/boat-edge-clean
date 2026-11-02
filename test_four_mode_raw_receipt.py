import hashlib
import json
import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from research_model import JST
from four_mode_raw_receipt import preserve


class RawSourceReceiptTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "raw"
        self.url = "https://boatracecsv.github.io/data/programs/title/2026/11/02.csv"
        self.received = datetime(2026, 11, 2, 12, 30, tzinfo=JST)
        self.env = patch.dict(os.environ, {"FOUR_MODE_RAW_RECEIPT_DIR": str(self.root)})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def test_preserves_exact_bytes_and_received_clock(self):
        source = b"\xef\xbb\xbfexample,raw\r\n"
        result = preserve(self.url, source, self.received)
        receipt = list(self.root.glob("*.json"))
        self.assertEqual(len(receipt), 1)
        metadata = json.loads(receipt[0].read_text())
        self.assertEqual(metadata["sha256"], hashlib.sha256(source).hexdigest())
        self.assertEqual(metadata["received_at_jst"], self.received.isoformat())
        self.assertFalse(metadata["independent_remote_receipt_verified"])
        self.assertEqual(list(self.root.glob("*.bin"))[0].read_bytes(), source)
        self.assertEqual(preserve(self.url, source, self.received)["sha256"], result["sha256"])

    def test_rejects_untrusted_host(self):
        with self.assertRaisesRegex(ValueError, "untrusted_source"):
            preserve("https://example.org/data.csv", b"x", self.received)

    def test_rejects_modified_existing_raw_bytes(self):
        preserve(self.url, b"original", self.received)
        list(self.root.glob("*.bin"))[0].write_bytes(b"tampered")
        with self.assertRaisesRegex(ValueError, "collision_or_change"):
            preserve(self.url, b"original", self.received)

    def test_disabled_is_no_op(self):
        with patch.dict(os.environ, {"FOUR_MODE_RAW_RECEIPT_DIR": ""}):
            self.assertIsNone(preserve(self.url, b"ok", self.received))


if __name__ == "__main__":
    unittest.main()
