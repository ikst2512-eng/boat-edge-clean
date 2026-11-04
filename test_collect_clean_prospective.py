import unittest
from datetime import datetime, timedelta
from research_model import JST
from collect_clean_prospective import build

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
    def test_refuses_generation_before_source_receipt(self):
        generated=datetime(2026,11,4,11,1,33,627045,tzinfo=JST)
        title_received=datetime(2026,11,4,11,1,33,708274,tzinfo=JST)
        cards_received=datetime(2026,11,4,11,1,33,766393,tzinfo=JST)
        title=[{"レースコード":"202611040404","電話投票締切予定":"12:16"}]
        cards=[{"レースコード":"202611040404",**{f"艇{i}_全国勝率":"5.1" for i in range(1,7)}}]
        self.assertEqual(build("20261104",title,cards,title_received,cards_received,
                               "a"*64,"b"*64,generated,{}),{})
        accepted=build("20261104",title,cards,title_received,cards_received,
                       "a"*64,"b"*64,datetime(2026,11,4,11,1,34,tzinfo=JST),{})
        self.assertIn("202611040404",accepted)
        self.assertFalse(accepted["202611040404"]["formal"])
        self.assertLessEqual(accepted["202611040404"]["source_cards_received_jst"],
                             accepted["202611040404"]["generated_at"])

    def test_naive_or_out_of_order_capture_times_not_published(self):
        now=datetime(2026,11,4,11,2,tzinfo=JST)
        title=[{"レースコード":"202611040404","電話投票締切予定":"12:16"}]
        cards=[{"レースコード":"202611040404",**{f"艇{i}_全国勝率":"5.1" for i in range(1,7)}}]
        self.assertEqual(build("20261104",title,cards,now.replace(tzinfo=None),
                               now,"a"*64,"b"*64,now,{}),{})

    def test_duplicate_inputs_rejected(self):
        now=datetime(2026,10,28,10,0,tzinfo=JST)
        row={"レースコード":"202610281201","電話投票締切予定":"14:00"}
        card={"レースコード":"202610281201",**{f"艇{i}_全国勝率":"5.1" for i in range(1,7)}}
        self.assertEqual(build("20261028",[row,row],[card],now,now,"a","b",now,{}),{})

if __name__=="__main__":
    unittest.main()
