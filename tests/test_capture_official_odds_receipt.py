import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
from scripts.capture_official_odds_receipt import capture

JST=timezone(timedelta(hours=9))
ODDS={f"{a}-{b}-{c}": "12.3" for a in range(1,7) for b in range(1,7)
      for c in range(1,7) if len({a,b,c})==3}

def clock():
    values=iter((datetime(2026,11,2,20,20,tzinfo=JST),
                 datetime(2026,11,2,20,20,8,tzinfo=JST)))
    return lambda: next(values)

class ImmutableOddsCaptureTests(unittest.TestCase):
    @patch("scripts.capture_official_odds_receipt.parse_official_odds_table",return_value=ODDS)
    def test_complete_pre_t12_still_research_only(self, parser):
        with tempfile.TemporaryDirectory() as d:
            out=capture("202611021512","2026-11-02T20:36:00+09:00",d,"attempt1",
                        fetch=lambda url:b"official-html-bytes",clock=clock())
            self.assertTrue(out["complete_odds_observed_before_t12"])
            self.assertFalse(out["forecast_usable"])
            saved=Path(d)/"observations/attempt1/20261102/202611021512"
            self.assertEqual((saved/"original.html").read_bytes(),b"official-html-bytes")
            self.assertEqual(json.loads((saved/"manifest.json").read_text())["sha256"],out["sha256"])
            with self.assertRaises(FileExistsError):
                capture("202611021512","2026-11-02T20:36:00+09:00",d,"attempt1",
                        fetch=lambda url:b"replace",clock=clock())

    @patch("scripts.capture_official_odds_receipt.parse_official_odds_table",return_value=ODDS)
    def test_late_receipt_not_pre_t12(self, parser):
        with tempfile.TemporaryDirectory() as d:
            out=capture("202611021512","2026-11-02T20:30:00+09:00",d,"one",
                        fetch=lambda url:b"source",clock=clock())
            self.assertFalse(out["complete_odds_observed_before_t12"])

    def test_invalid_response_or_deadline_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                capture("202611021512","2026-11-02T11:36:00+00:00",d,"one",
                        fetch=lambda url:b"source",clock=clock())
            with patch("scripts.capture_official_odds_receipt.parse_official_odds_table",side_effect=ValueError("bad")):
                out=capture("202611021512","2026-11-02T20:36:00+09:00",d,"two",
                            fetch=lambda url:b"bad",clock=clock())
            self.assertEqual(out["status"],"official_odds_probe_failed")
            self.assertFalse(list(Path(d).rglob("original.html")))

if __name__=="__main__":
    unittest.main()
