import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from four_mode_v2_venue_coverage import venue_audit, VERSION

JST = timezone(timedelta(hours=9))
def records():
    combos = ["1-2-3","1-2-4","1-3-2","2-1-3","3-1-2",
              "1-4-2","2-3-1","3-2-1","4-1-2","5-1-2"]
    ticket = [{"combo": c, "p": 10-i} for i,c in enumerate(combos)]
    return {"model_version": VERSION, "deadline_jst": "2026-11-03T13:00:00+09:00",
            "modes": {"hit": {"tickets":ticket},
                      "narrow": {"tickets": [{}]*5},
                      "balance": {"tickets": [{}]*16},
                      "hole": {"tickets": [{}]*22}}}

class VenueResearchTests(unittest.TestCase):
    def test_venue_missingness_and_exact_same_venue_denominator(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            folder = root/"four_mode_forecasts"
            folder.mkdir()
            codes=("202611030101","202611030102","202611030201")
            for code in codes:
                (folder/(code+".json")).write_text(json.dumps({
                    "race_code":code,"model_version":VERSION,
                    "input_national_win_rates":[5]*6}))
            def compare(code, root):
                if code.endswith("01") and code[8:10]=="01":
                    return {"status":"historical_comparison_only",
                            "modes":{m:{f"top{n}":True for n in (3,5,10)}
                                     for m in ("hit","balance","narrow","hole")}}
                return {"status":"result_unavailable"}
            with patch("four_mode_v2_venue_coverage.archived_four_modes",
                       return_value=(200,records())), patch(
                       "four_mode_v2_venue_coverage.compare_race",side_effect=compare):
                result=venue_audit(root,now=datetime(2026,11,3,15,30,tzinfo=JST))
            self.assertEqual(result["total_saved"],3)
            self.assertEqual(result["total_confirmed"],1)
            self.assertEqual(result["total_overdue_missing"],2)
            self.assertEqual(result["total_missing_file_absent"], 2)
            self.assertEqual(result["total_missing_file_present_but_unavailable"], 0)
            self.assertEqual(result["venues"]["20261103:01"]["overdue_example_race_codes"], ["202611030102"])
            self.assertEqual(result["venues"]["20261103:02"]["overdue_example_race_codes"], ["202611030201"])
            self.assertEqual(result["venues"]["20261103:01"]["mature_coverage"],0.5)
            self.assertEqual(result["venues"]["20261103:02"]["mature_coverage"],0)
            self.assertEqual(result["distinct_venues_with_confirmed"],1)
            self.assertFalse(result["formal"])

    def test_overdue_present_file_not_a_confirmed_result(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            folder = root / "four_mode_forecasts"
            folder.mkdir()
            code = "202611030101"
            (folder / (code+".json")).write_text(json.dumps({
                "race_code":code,"model_version":VERSION,
                "input_national_win_rates":[5]*6}))
            results = root / "confirmed_results"
            results.mkdir()
            (results / (code + ".json")).write_text("{}")
            with patch("four_mode_v2_venue_coverage.archived_four_modes",
                       return_value=(200, records())), patch(
                       "four_mode_v2_venue_coverage.compare_race",
                       return_value={"status": "result_unavailable"}):
                report = venue_audit(root, now=datetime(2026,11,3,15,30,tzinfo=JST))
            self.assertEqual(report["total_missing_file_absent"],0)
            self.assertEqual(report["total_missing_file_present_but_unavailable"],1)
            self.assertEqual(report["total_confirmed"],0)

    def test_no_v2_denominator_not_zero_accuracy(self):
        with tempfile.TemporaryDirectory() as td:
            (Path(td)/"four_mode_forecasts").mkdir()
            result=venue_audit(td)
            self.assertEqual(result["total_saved"],0)
            self.assertEqual(result["venues"],{})
            self.assertFalse(result["formal"])

if __name__ == "__main__":
    unittest.main()
