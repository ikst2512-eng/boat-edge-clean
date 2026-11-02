import json
import tempfile
import unittest
from pathlib import Path
from four_mode_frozen_diagnostic import compare_race

CODE = "202610280101"

def archive():
    return {"schema":"CLEAN_FOUR_MODES_PREDEADLINE_V1","race_code":CODE,
            "generated_at_jst":"2026-10-28T10:00:00+09:00",
            "deadline_jst":"2026-10-28T14:00:00+09:00",
            "modes":{m:{"tickets":[{"combo":ticket,"p":4.5}]} for m,ticket in
                     (("hit","1-2-3"),("balance","2-1-3"),("hole","3-1-2"),("narrow","4-1-2"))}}

class FrozenFourModeDiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root/"four_mode_forecasts").mkdir()
        (self.root/"confirmed_results").mkdir()
        (self.root/"four_mode_forecasts"/(CODE+".json")).write_text(json.dumps(archive()))
        self.result = self.root/"confirmed_results"/(CODE+".json")
        self.result.write_text(json.dumps({"race_code":CODE,"status":"confirmed",
            "finish_order":[1,2,3],"source_url":"https://example.org/results"}))
    def tearDown(self):
        self.tmp.cleanup()
    def test_uses_only_frozen_mode_tickets(self):
        r=compare_race(CODE,self.root)
        self.assertEqual(r["status"],"historical_comparison_only")
        self.assertEqual([r["modes"][m]["hit"] for m in ("hit","balance","hole","narrow")],
                         [True,False,False,False])
        self.assertEqual(r["modes"]["hit"]["winning_rank"], 1)
        self.assertTrue(r["modes"]["hit"]["top3"])
        self.assertFalse(r["modes"]["balance"]["top10"])
        self.assertFalse(r["formal"])
        self.assertFalse(r["remote_first_seen_verified"])
        self.assertNotIn("roi",r)
    def test_missing_result_is_not_a_loss(self):
        self.result.unlink()
        self.assertEqual(compare_race(CODE,self.root)["status"],"result_unavailable")
    def test_invalid_result_never_scores(self):
        self.result.write_text(json.dumps({"race_code":CODE,"status":"confirmed",
            "finish_order":[1,1,3],"source_url":"https://example.org/results"}))
        self.assertEqual(compare_race(CODE,self.root)["status"],"invalid_result_or_timing")
    def test_wrong_date_is_not_formally_promoted(self):
        a=archive()
        a["deadline_jst"]="2026-10-29T14:00:00+09:00"
        (self.root/"four_mode_forecasts"/(CODE+".json")).write_text(json.dumps(a))
        self.assertEqual(compare_race(CODE,self.root)["status"],"invalid_result_or_timing")

if __name__=="__main__":
    unittest.main()
