import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from research_model import probabilities
from entry_course_prospective_capture import prepare_prospective_capture
from entry_course_prospective_audit import audit_frozen_comparison
from entry_course_write_once import freeze_capture

JST=timezone(timedelta(hours=9))
CUTOFF="2026-11-03T19:08:00+09:00"
BEFORE="2026-11-03T18:30:00+09:00"
BASE_RATES=[5.5,6.0,6.3,4.9,5.2,5.7]

def fixture():
    original=["-".join(map(str,t)) for t,p in probabilities(BASE_RATES)]
    base={"race_code":"202611030708","cutoff_jst":CUTOFF,
          "generated_at":"2026-11-03T18:00:00+09:00",
          "predictions":original[:10],"national_win_rates":BASE_RATES,
          "status":"research","validated":False,
          "source_deadline_jst":"2026-11-03T19:20:00+09:00",
          "source_cards_sha256":"a"*64,"source_title_sha256":"b"*64,
          "input_sha256":"c"*64,"model_source_sha256":"d"*64}
    card={"race_key":"20261103-07-08",
          "meta":{"phase":"PRE_RESULT","results_seen":False},
          "racers":[{"lane":i,"registration_no":str(4000+i)} for i in range(1,7)],
          "beforeinfo":{"start_exhibition":[{"lane":i,"course":float(i),"st":"0.15"} for i in range(1,7)]},
          "source_audit":{"beforeinfo":{"status":"ok","sources":{
              "stt":{"observed_at":BEFORE,"sha256":"e"*64},
              "tkz":{"observed_at":BEFORE,"sha256":"f"*64}}}}}
    code="202611020701"
    historical_card={"レースコード":code,**{f"艇{i}_登録番号":str(4000+i) for i in range(1,7)}}
    result={"レースコード":code,"取得日時":"2026-11-02T16:00:00+09:00",
            "決まり手":"逃げ"}
    for i in range(1,7):
        result[f"{i}着_艇番"]=str(i)
        result[f"{i}コース_艇番"]=str(i)
        result[f"{i}コース_スタートタイミング"]="0.15"
    historical={"race_card":historical_card,"result":result,
                "card_receipt_at":BEFORE,"result_receipt_at":BEFORE,
                "card_sha256":"1"*64,"result_sha256":"2"*64}
    batch={"target_day":"20261103","cutoff_at":CUTOFF,
           "research_only":True,"history":[historical],"failed_sources":[]}
    return base,card,batch

class ProspectiveCaptureTests(unittest.TestCase):
    def test_real_clean_float_course_numbers_and_complete_three_rankings(self):
        base,card,batch=fixture()
        c=prepare_prospective_capture(base,card,batch,frozen_at=BEFORE,min_starts=1)
        self.assertEqual(c["entry"],[1,2,3,4,5,6])
        self.assertEqual(c["entry_source"],"third_party_timestamped_preview")
        self.assertEqual(len(c["baseline"]),120)
        self.assertEqual(c["baseline"][:10],base["predictions"])
        self.assertEqual(len(c["course"]),120)
        self.assertEqual(len(c["course_plus_st"]),120)
        self.assertFalse(c.get("formal_forecast_approved",False))
        audit=audit_frozen_comparison(base,c)
        self.assertTrue(audit["comparison_ready"])
        self.assertFalse(audit["can_score"])
    def test_no_course_sample_blocks_capture(self):
        base,card,batch=fixture()
        with self.assertRaisesRegex(ValueError,"insufficient_course"):
            prepare_prospective_capture(base,card,batch,frozen_at=BEFORE,min_starts=10)
    def test_late_capture_is_blocked(self):
        base,card,batch=fixture()
        with self.assertRaisesRegex(ValueError,"capture_not_pre_cutoff"):
            prepare_prospective_capture(base,card,batch,frozen_at="2026-11-03T19:10:00+09:00",min_starts=1)
    def test_pre_result_required(self):
        base,card,batch=fixture()
        card["meta"]["results_seen"]=True
        with self.assertRaisesRegex(ValueError,"racecard_not_pre_result"):
            prepare_prospective_capture(base,card,batch,frozen_at=BEFORE,min_starts=1)
    def test_snapshot_baseline_rank_drift_is_rejected(self):
        base,card,batch=fixture()
        base["predictions"]=list(reversed(base["predictions"]))
        with self.assertRaisesRegex(ValueError,"baseline_rank_drift"):
            prepare_prospective_capture(base,card,batch,frozen_at=BEFORE,min_starts=1)
    def test_no_late_preview_provenance(self):
        base,card,batch=fixture()
        card["source_audit"]["beforeinfo"]["sources"]["stt"]["observed_at"]="2026-11-03T19:11:00+09:00"
        with self.assertRaisesRegex(ValueError,"preview_stt_receipt"):
            prepare_prospective_capture(base,card,batch,frozen_at=BEFORE,min_starts=1)
    def test_write_once_refuses_overwrite_or_late_write(self):
        base,card,batch=fixture()
        c=prepare_prospective_capture(base,card,batch,frozen_at=BEFORE,min_starts=1)
        with tempfile.TemporaryDirectory() as tmp:
            clock=lambda:datetime(2026,11,3,18,32,tzinfo=JST)
            path=freeze_capture(c,tmp,clock=clock)
            self.assertTrue(path.is_file())
            with self.assertRaises(FileExistsError):
                freeze_capture(c,tmp,clock=clock)
            with self.assertRaisesRegex(ValueError,"capture_write_after_cutoff"):
                freeze_capture(c,tmp,clock=lambda:datetime(2026,11,3,19,9,tzinfo=JST))
if __name__=="__main__":unittest.main()
