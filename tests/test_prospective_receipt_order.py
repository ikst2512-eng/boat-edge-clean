import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import server


class ArchivedReceiptOrderTest(unittest.TestCase):
    def test_research_candidate_flags_inverted_source_receipt_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "prospective_predictions").mkdir()
            record = {
                "race_code": "202610310708",
                "status": "prospective_candidate",
                "validated": False,
                "generated_at": "2026-10-31T10:27:33.651377+09:00",
                "cutoff_jst": "2026-10-31T18:21:00+09:00",
                "source_title_received_jst": "2026-10-31T10:27:33.810972+09:00",
                "source_cards_received_jst": "2026-10-31T10:27:33.974239+09:00",
                "model_version": "test-research-model",
                "predictions": ["1-2-3", "1-2-4", "1-2-5", "1-2-6",
                                "1-3-2", "1-3-4", "1-3-5", "1-3-6",
                                "1-4-2", "1-4-3"],
            }
            path = root / "prospective_predictions" / "202610310708.json"
            path.write_text(json.dumps(record), encoding="utf-8")
            with patch.object(server, "ROOT", root):
                status, response = server.get_predictions(
                    {"hd": ["20261031"], "jcd": ["07"], "rno": ["8"]})
                self.assertEqual(status, 200)
                self.assertEqual(response["status"], "research")
                self.assertFalse(response["validated"])
                self.assertFalse(response["receipt_order_verified"])
                self.assertEqual(response["provenance_warning"], "SOURCE_RECEIPT_ORDER_UNVERIFIED")
                record["generated_at"] = "2026-10-31T10:28:00+09:00"
                path.write_text(json.dumps(record), encoding="utf-8")
                status, response = server.get_predictions(
                    {"hd": ["20261031"], "jcd": ["07"], "rno": ["8"]})
                self.assertEqual(status, 200)
                self.assertTrue(response["receipt_order_verified"])
                self.assertIsNone(response["provenance_warning"])


if __name__ == "__main__":
    unittest.main()
