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
            self.assertEqual(json.loads(path.read_text(encoding='utf-8'))['http_status'],404)
            old=path.read_bytes()
            publish_status({"new_saved":[],"source_pending":"waiting_for_published_source",
                "http_status":404,"source_url":state["source_url"]},root,now)
            self.assertEqual(old,path.read_bytes())
    def test_both_sources_probed_on_title_404(self):
        from urllib.error import HTTPError
        from unittest.mock import Mock
        from clean_four_mode_capture import collect
        with tempfile.TemporaryDirectory() as tmp:
            calls=[]
            def fake_read(url):
                calls.append(url)
                if "/title/" in url:
                    raise HTTPError(url,404,"Not Found",None,None)
                return ([{"レースコード":"202610280101"}],datetime(2026,10,28,7,0,tzinfo=JST),"a"*64)
            result=collect(root=Path(tmp),now=datetime(2026,10,28,7,0,tzinfo=JST),read=fake_read)
            self.assertEqual(len(calls),2)
            self.assertEqual(result["source_probes"]["title"]["http_status"],404)
            self.assertEqual(result["source_probes"]["race_cards"]["status"],"available")
            self.assertEqual(result["eligible_forecasts_today"],0)
    def test_direct_403_keeps_blocked_url_distinct_from_unpublished_404(self):
        from urllib.error import HTTPError
        from unittest.mock import patch
        from clean_four_mode_capture import collect
        with tempfile.TemporaryDirectory() as tmp:
            now=datetime(2026,10,29,7,0,tzinfo=JST)
            def unpublished(url):
                raise HTTPError(url,404,"Not Found",None,None)
            blocked="https://race.boatcast.jp/api_txt/getHoldingList2_20261029.json"
            def blocked_holding(day):
                raise HTTPError(blocked,403,"Forbidden",None,None)
            with patch("clean_direct_sources.holding_rows",side_effect=blocked_holding),patch("clean_openapi_sources.load",side_effect=ValueError("unavailable_fixture")):
                result=collect(root=Path(tmp),now=now,read=unpublished)
            self.assertEqual(result["source_status"],"source_blocked")
            self.assertEqual(result["source_probes"]["title"]["status"],"not_published")
            self.assertEqual(result["source_probes"]["race_cards"]["status"],"not_published")
            direct=result["source_probes"]["direct_error"]
            self.assertEqual(direct["http_status"],403)
            self.assertEqual(direct["source_url"],blocked)
            self.assertEqual(result["new_saved"],[])

    def test_archived_forecasts_counted_separately(self):
        with tempfile.TemporaryDirectory() as tmp:
            state=publish_status({"new_saved":["202610280101"],"source_status":"available",
                "eligible_forecasts_today":1,"published_title_rows":100,"published_card_rows":100},
                Path(tmp),datetime(2026,10,28,6,0,tzinfo=JST))
            self.assertTrue(state["production_success_proven"])


if __name__=="__main__":unittest.main()
