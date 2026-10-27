import json
import tempfile
import unittest
from pathlib import Path
from datetime import datetime
from unittest.mock import patch
import collect_clean_results as c


class ResultCollectorTests(unittest.TestCase):
    def test_source_validated(self):
        header="レースコード,取得日時,1着_艇番,2着_艇番,3着_艇番\n"
        row="202610270101,2026-10-27T16:00:00+09:00,1,2,3\n"
        records=c.build_records("20261027",(header+row).encode(),datetime.fromisoformat("2026-10-27T17:00:00+09:00"))
        self.assertEqual(records["202610270101"]["finish_order"],[1,2,3])
        self.assertIn("boatracecsv.github.io",records["202610270101"]["source_url"])
    def test_rejects_duplicate_codes(self):
        header="レースコード,取得日時,1着_艇番,2着_艇番,3着_艇番\n"
        row="202610270101,2026-10-27T16:00:00+09:00,1,2,3\n"
        with self.assertRaises(ValueError):
            c.build_records("20261027",(header+row+row).encode(),datetime.fromisoformat("2026-10-27T17:00:00+09:00"))
    def test_no_invalid_finishes(self):
        raw="レースコード,取得日時,1着_艇番,2着_艇番,3着_艇番\n202610270101,2026-10-27T16:00:00+09:00,1,1,3\n"
        self.assertFalse(c.build_records("20261027",raw.encode(),datetime.fromisoformat("2026-10-27T17:00:00+09:00")))


if __name__=="__main__":
    unittest.main()
