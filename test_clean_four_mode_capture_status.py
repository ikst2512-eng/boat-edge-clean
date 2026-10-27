import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from clean_four_mode_capture import publish_status
from research_model import JST


class CaptureStatusTests(unittest.TestCase):
    def test_missing_input_never_claims_production_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            now=datetime(2026,10,28,7,0,tzinfo=JST)
            state=publish_status({"new_saved":[],"source_pending":"waiting_for_published_source",
                "http_status":404,"source_url":"https://boatracecsv.github.io/data/programs/race_cards/2026/10/28.csv",
                "retryable":True},root,now)
            self.assertFalse(state["production_success_proven"])
            self.assertEqual(state["http_status"],404)
            self.assertEqual(state["eligible_forecasts_today"],0)
            path=root/"four_mode_forecasts/capture_status.json"
            old=path.read_bytes()
            publish_status({"new_saved":[],"source_pending":"waiting_for_published_source",
                "http_status":404,"source_url":state["source_url"]},root,now)
            self.assertEqual(old,path.read_bytes())
    def test_archived_forecasts_counted_separately(self):
        with tempfile.TemporaryDirectory() as tmp:
            state=publish_status({"new_saved":["202610280101"],"source_status":"available",
                "eligible_forecasts_today":1,"published_title_rows":100,"published_card_rows":100},
                Path(tmp),datetime(2026,10,28,6,0,tzinfo=JST))
            self.assertTrue(state["production_success_proven"])


if __name__=="__main__":unittest.main()
