import unittest
from datetime import datetime, timedelta
from research_model import JST
from collect_clean_prospective import build, finalize_records

class ProspectiveTests(unittest.TestCase):
    def test_pre_cutoff_and_no_formal_promotion(self):
        now=datetime(2026,10,28,10,0,tzinfo=JST)
        title=[{"レースコード":"202610281201","電話投票締切予定":"14:00"}]
        card=[{"レースコード":"202610281201",**{f"艇{i}_全国勝率":"5.1" for i in range(1,7)}}]
        rows=build("20261028",title,card,now,now,"a"*64,"b"*64,now,{"model_git_sha":"a"*40,"model_source_sha256":"b"*64})
        r=rows["202610281201"]
        self.assertFalse(r["formal"])
        self.assertFalse(r["scoring"])
        self.assertEqual(len(r["predictions"]),10)
        late=build("20261028",title,card,now,now,"a"*64,"b"*64,datetime(2026,10,28,13,49,tzinfo=JST),{})
        self.assertEqual(late,{})
    def test_finalized_generation_timestamp_is_after_input_receipts(self):
        now=datetime(2026,11,4,11,0,0,tzinfo=JST)
        title=[{"レースコード":"202611040404","電話投票締切予定":"12:16"}]
        card=[{"レースコード":"202611040404",**{f"艇{i}_全国勝率":"5.1" for i in range(1,7)}}]
        title_time=now+timedelta(milliseconds=100)
        cards_time=now+timedelta(milliseconds=200)
        tentative=build("20261104",title,card,title_time,cards_time,"a"*64,"b"*64,
                        now+timedelta(milliseconds=201),{})
        completed=now+timedelta(milliseconds=400)
        saved=finalize_records(tentative,title_time,cards_time,completed)
        self.assertEqual(saved["202611040404"]["generated_at"],completed.isoformat())
        self.assertLessEqual(cards_time,datetime.fromisoformat(saved["202611040404"]["generated_at"]))
        # Existing stored records must never be rewritten by the helper.
        self.assertEqual(tentative["202611040404"]["generated_at"],
                         (now+timedelta(milliseconds=201)).isoformat())

    def test_finalization_excludes_records_that_cross_twelve_minute_cutoff(self):
        now=datetime(2026,11,4,12,3,58,tzinfo=JST)
        title=[{"レースコード":"202611040404","電話投票締切予定":"12:16"}]
        card=[{"レースコード":"202611040404",**{f"艇{i}_全国勝率":"5.1" for i in range(1,7)}}]
        source_time=now
        tentative=build("20261104",title,card,source_time,source_time,"a","b",now,{})
        self.assertIn("202611040404",tentative)
        self.assertEqual(finalize_records(tentative,source_time,source_time,
                         datetime(2026,11,4,12,4,tzinfo=JST)),{})
        self.assertEqual(finalize_records(tentative,source_time,source_time,
                         datetime(2026,11,4,12,3,59,tzinfo=JST))["202611040404"]["generated_at"],
                         "2026-11-04T12:03:59+09:00")

    def test_duplicate_inputs_rejected(self):
        now=datetime(2026,10,28,10,0,tzinfo=JST)
        row={"レースコード":"202610281201","電話投票締切予定":"14:00"}
        card={"レースコード":"202610281201",**{f"艇{i}_全国勝率":"5.1" for i in range(1,7)}}
        self.assertEqual(build("20261028",[row,row],[card],now,now,"a","b",now,{}),{})

if __name__=="__main__":
    unittest.main()
