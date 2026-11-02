import hashlib
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from four_mode_raw_receipt import preserve
from link_four_mode_raw_forecast import link_forecast
from research_model import JST

class LinkTest(unittest.TestCase):
    def test_match_and_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/"four_mode_forecasts").mkdir()
            d=root/"raw"
            t=b"title"; c=b"cards"
            with patch.dict("os.environ", {"FOUR_MODE_RAW_RECEIPT_DIR": str(d)}):
                for url,raw in (("https://boatracecsv.github.io/data/programs/title/t.csv",t),
                                ("https://boatracecsv.github.io/data/programs/race_cards/c.csv",c)):
                    preserve(url,raw,datetime(2026,11,2,11,0,tzinfo=JST))
            code="202611020101"
            path=root/"four_mode_forecasts"/(code+".json")
            path.write_text(json.dumps({"race_code":code,"source_sha256":{
                "title":hashlib.sha256(t).hexdigest(),"race_cards":hashlib.sha256(c).hexdigest()}}))
            yes=link_forecast(code,root,d)
            self.assertEqual(yes["status"],"both_hashes_present")
            self.assertFalse(yes["formal"])
            path.write_text(json.dumps({"race_code":code,"source_sha256":{
                "title":hashlib.sha256(t).hexdigest(),"race_cards":"a"*64}}))
            self.assertEqual(link_forecast(code,root,d)["status"],"incomplete_source_link")
            self.assertEqual(link_forecast(code,root,root/"missing")["status"],"raw_receipts_unverified")
if __name__=="__main__":
    unittest.main()
