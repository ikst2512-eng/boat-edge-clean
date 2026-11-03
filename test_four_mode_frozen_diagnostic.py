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
            "finish_order":[1,2,3],"source_url":"https://example.org/results",
            "source_sha256":"a"*64,
            "confirmed_at_jst":"2026-10-28T14:01:00+09:00",
            "collected_at_jst":"2026-10-28T14:02:00+09:00"}))
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
        self.assertEqual(r["modes"]["balance"]["coverage_diagnostic"], "winner_head_absent")
        self.assertEqual(r["modes"]["hit"]["coverage_diagnostic"], "covered")
        self.assertEqual(r["modes"]["hole"]["race_dynamics_cause"], "not_determined")
        self.assertFalse(r["formal"])
        self.assertFalse(r["remote_first_seen_verified"])
        self.assertNotIn("roi",r)
    def test_miss_taxonomy_uses_only_frozen_tickets(self):
        a = archive()
        a["modes"]["balance"]["tickets"] = [{"combo": "1-3-2", "p": 4.5}]
        a["modes"]["hole"]["tickets"] = [{"combo": "1-2-4", "p": 4.5}]
        (self.root/"four_mode_forecasts"/(CODE+".json")).write_text(json.dumps(a))
        modes = compare_race(CODE, self.root)["modes"]
        self.assertEqual(modes["balance"]["coverage_diagnostic"], "winner_second_pair_absent")
        self.assertEqual(modes["hole"]["coverage_diagnostic"], "winner_third_absent")

    def test_missing_result_is_not_a_loss(self):
        self.result.unlink()
        self.assertEqual(compare_race(CODE,self.root)["status"],"result_unavailable")
    def test_invalid_result_never_scores(self):
        self.result.write_text(json.dumps({"race_code":CODE,"status":"confirmed",
            "finish_order":[1,1,3],"source_url":"https://example.org/results"}))
        self.assertEqual(compare_race(CODE,self.root)["status"],"invalid_result_or_timing")
    def test_corrupt_confirmed_result_is_not_scored(self):
        good=json.loads(self.result.read_text(encoding="utf-8"))
        for bad in (
            dict(good,source_sha256="not-a-hash"),
            dict(good,confirmed_at_jst="2026-10-28T14:01:00"),
            dict(good,collected_at_jst="not-a-date"),
            dict(good,source_url="http://example.org/results"),
            dict(good,race_code="202610280102"),
        ):
            with self.subTest(bad=bad):
                self.result.write_text(json.dumps(bad),encoding="utf-8")
                outcome=compare_race(CODE,self.root)
                self.assertEqual(outcome["status"],"invalid_result_or_timing")
                self.assertFalse(outcome["formal"])

    def test_future_dated_persisted_result_is_not_scored(self):
        record=json.loads(self.result.read_text(encoding="utf-8"))
        record["confirmed_at_jst"]="2026-10-28T14:05:01+09:00"
        record["collected_at_jst"]="2026-10-28T14:02:00+09:00"
        self.result.write_text(json.dumps(record),encoding="utf-8")
        outcome=compare_race(CODE,self.root)
        self.assertEqual(outcome["status"],"invalid_result_or_timing")
        self.assertFalse(outcome["formal"])

    def test_wrong_date_is_not_formally_promoted(self):
        a=archive()
        a["deadline_jst"]="2026-10-29T14:00:00+09:00"
        (self.root/"four_mode_forecasts"/(CODE+".json")).write_text(json.dumps(a))
        self.assertEqual(compare_race(CODE,self.root)["status"],"invalid_result_or_timing")

if __name__=="__main__":
    unittest.main()
