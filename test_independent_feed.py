import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import independent_feed as feed


class IndependentFeedTests(unittest.TestCase):
    def test_rejects_invalid_key(self):
        self.assertEqual(feed.research_snapshot("20261027", "../", 1)[0], 400)

    def test_no_legacy_fallback(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(feed, "ROOT", Path(tmp)):
            status, data = feed.research_snapshot("20261027", "01", "01")
        self.assertEqual((status, data["status"]), (404, "not_collected"))

    def test_archive_is_never_formal(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(feed, "ROOT", Path(tmp)):
            archive = Path(tmp) / "research_snapshots"
            archive.mkdir()
            (archive / "202610270101.json").write_text(json.dumps({
                "race_code": "202610270101", "status": "research", "validated": False,
                "predictions": ["1-2-3","1-2-4","1-3-2","1-3-4","1-4-2",
                                "1-4-3","2-1-3","2-1-4","2-3-1","2-3-4"],
                "model_version": "research-test", "generated_at": "2026-10-27T09:00:00+09:00"
            }), encoding="utf-8")
            status, data = feed.research_snapshot("20261027", 1, 1)
        self.assertEqual(status, 200)
        self.assertFalse(data["formal"])
        self.assertFalse(data["scoring"])
        self.assertFalse(data["validated"])


if __name__ == "__main__":
    unittest.main()
