import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from research_model import JST
from four_mode_raw_receipt import preserve
from audit_four_mode_raw_receipts import audit

class AuditRawReceiptsTests(unittest.TestCase):
    def test_integrity_and_mutation(self):
        with tempfile.TemporaryDirectory() as folder:
            d = Path(folder)
            with patch.dict("os.environ", {"FOUR_MODE_RAW_RECEIPT_DIR": folder}):
                preserve("https://boatracecsv.github.io/data/programs/title/2026/11/02.csv",
                         b"original", datetime(2026,11,2,14,0,tzinfo=JST))
            self.assertEqual(audit(d)["status"], "local_integrity_verified")
            list(d.glob("*.bin"))[0].write_bytes(b"modified")
            self.assertEqual(audit(d)["status"], "invalid_receipt")

    def test_missing_receipts_not_success(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(audit(folder)["status"], "no_receipts")

if __name__ == "__main__":
    unittest.main()
