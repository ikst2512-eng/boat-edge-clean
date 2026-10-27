import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from datetime import datetime
import capture_clean_schedule as cap

class CaptureTests(unittest.TestCase):
    def test_creates_and_preserves_first_snapshot(self):
        sample={"date":"20261028","source_sha256":"a"*64,
                "source_received_jst":"2026-10-28T07:00:00+09:00",
                "races":[{"venue_code":"12","race_no":1,"deadline_jst":"2026-10-28T15:16:00+09:00"}]}
        with tempfile.TemporaryDirectory() as root, patch.object(cap,"ROOT",Path(root)), patch.object(cap,"clean_schedule",return_value=(200,sample)):
            self.assertEqual(cap.capture("20261028")["saved"],1)
            self.assertEqual(cap.capture("20261028")["already_saved"],1)
            import json
            data=json.loads((Path(root)/"schedule_snapshots/20261028.json").read_text())
        self.assertFalse(data["scoring"])
        self.assertEqual(data["venues"][0]["races"][0]["deadline"],"15:16")
    def test_early_jst_source_wait(self):
        with patch.object(cap, "datetime") as clock, patch.object(cap, "clean_schedule") as fetch:
            clock.now.return_value = datetime(2026,10,28,1,10,tzinfo=cap.JST)
            result = cap.capture("20261028")
            self.assertEqual(result["status"], "waiting_for_published_source")
            fetch.assert_not_called()

    def test_no_fallback_on_unavailable_source(self):
        with patch.object(cap,"clean_schedule",return_value=(503,{"status":"source_unavailable"})):
            with self.assertRaises(ValueError):
                cap.capture("20261027")
if __name__=="__main__":
    unittest.main()
