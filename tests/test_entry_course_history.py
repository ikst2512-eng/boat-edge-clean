"""Leakage and permutation tests for historical course statistics."""
import unittest
from copy import deepcopy
from entry_course_history import compile_asof_course_history

CUTOFF="2026-11-03T19:08:00+09:00"
AT="2026-11-02T12:00:00+09:00"
TARGET={"race_key":"20261103-07-08","racers":[{"lane":i,"registration_no":str(4000+i)} for i in range(1,7)]}
def historical(day=1, *, receipt=AT, published=AT):
    code=f"202610{day:02d}0701"
    card={"レースコード":code,**{f"艇{i}_登録番号":str(4000+i) for i in range(1,7)}}
    result={"レースコード":code,"取得日時":published,"決まり手":"逃げ"}
    for pos,boat in enumerate([2,1,3,4,5,6],1):
        result[f"{pos}着_艇番"]=str(boat)
    for course,boat in enumerate([2,1,3,4,5,6],1):
        result[f"{course}コース_艇番"]=str(boat)
        result[f"{course}コース_スタートタイミング"]="0.14"
    return dict(race_card=card,result=result,card_receipt_at=receipt,result_receipt_at=receipt,
                card_sha256="a"*64,result_sha256="b"*64)
class CourseHistoryTests(unittest.TestCase):
    def build(self,rows,entry=None,min_starts=10):
        return compile_asof_course_history(TARGET,rows,cutoff_at=CUTOFF,
            entry=entry or [2,1,3,4,5,6],min_starts=min_starts)
    def test_course_swaps_track_registration_and_real_course(self):
        result=self.build([historical(i) for i in range(1,11)])
        self.assertTrue(result["history_sufficient"])
        self.assertEqual(result["eligible_races"],10)
        one,two=result["boats"][:2]
        self.assertEqual((one["boat"],one["course"],one["registration_no"]),(2,1,"4002"))
        self.assertEqual(one["courseWinRate"],1.0)
        self.assertEqual(one["first_place_decisions"]["逃げ"],10)
        self.assertEqual(two["courseTop2Rate"],1.0)
        self.assertEqual(two["courseWinRate"],0)
        self.assertFalse(result["formal_forecast_approved"])
    def test_real_nov2_csv_spaced_decision_normalizes_without_changing_outcome(self):
        # Actual realtime CSV 2026-11-02 row uses full-width gap: 逃　げ.
        row=historical()
        row["result"]["決まり手"]="逃　げ"
        out=self.build([row],min_starts=1)
        self.assertEqual(out["eligible_races"],1)
        self.assertEqual(out["boats"][0]["first_place_decisions"],{"逃げ":1})
        self.assertEqual(out["boats"][0]["courseWinRate"],1.0)
    def test_unknown_decision_remains_unknown_without_guess(self):
        row=historical()
        row["result"]["決まり手"]="不明"
        out=self.build([row],min_starts=1)
        self.assertEqual(out["eligible_races"],1)
        self.assertEqual(out["boats"][0]["first_place_decisions"],{})
    def test_late_receipt_not_counted(self):
        late=historical(1,receipt="2026-11-03T19:09:00+09:00")
        result=self.build([late])
        self.assertEqual(result["eligible_races"],0)
        self.assertEqual(result["excluded"]["receipt_not_asof"],1)
    def test_future_and_target_days_excluded(self):
        row=historical()
        row["race_card"]["レースコード"]="202611030701"
        row["result"]["レースコード"]="202611030701"
        result=self.build([row])
        self.assertEqual(result["eligible_races"],0)
        self.assertEqual(result["excluded"]["wrong_race_or_future_day"],1)
    def test_duplicate_race_cannot_inflate_sample(self):
        row=historical()
        result=self.build([row,deepcopy(row)],min_starts=1)
        self.assertEqual(result["eligible_races"],1)
        self.assertEqual(result["excluded"]["duplicate_race"],1)
    def test_missing_finish_rejects_complete_race(self):
        row=historical()
        row["result"].pop("6着_艇番")
        self.assertEqual(self.build([row])["eligible_races"],0)
    def test_published_after_cutoff_rejected_even_if_receipt_is_earlier(self):
        row=historical(published="2026-11-03T19:09:00+09:00")
        self.assertEqual(self.build([row])["eligible_races"],0)
    def test_no_national_rate_fallback_when_course_sample_empty(self):
        result=self.build([])
        self.assertFalse(result["history_sufficient"])
        self.assertEqual(result["boats"][0]["courseWinRate"],None)
        self.assertEqual(result["boats"][0]["courseAverageST"],None)
    def test_missing_digest_rejected(self):
        row=historical();row["result_sha256"]=None
        self.assertEqual(self.build([row])["excluded"]["missing_source_digest"],1)
    def test_f_st_not_used_for_normal_mean(self):
        row=historical();row["result"]["1コース_スタートタイミング"]="-0.01"
        result=self.build([row],min_starts=1)
        self.assertEqual(result["boats"][0]["courseStarts"],1)
        self.assertIsNone(result["boats"][0]["courseAverageST"])
        self.assertFalse(result["history_sufficient"])
    def test_wrong_registrations_rejected(self):
        row=historical();row["race_card"]["艇1_登録番号"]="4002"
        self.assertEqual(self.build([row])["excluded"]["invalid_registration"],1)
    def test_wrong_course_mapping_rejected(self):
        row=historical();row["result"]["1コース_艇番"]="1"
        self.assertEqual(self.build([row])["excluded"]["incomplete_result"],1)
if __name__=="__main__": unittest.main()
