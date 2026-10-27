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
    def test_duplicate_inputs_rejected(self):
        now=datetime(2026,10,28,10,0,tzinfo=JST)
        row={"レースコード":"202610281201","電話投票締切予定":"14:00"}
        card={"レースコード":"202610281201",**{f"艇{i}_全国勝率":"5.1" for i in range(1,7)}}
        self.assertEqual(build("20261028",[row,row],[card],now,now,"a","b",now,{}),{})

if __name__=="__main__":
    unittest.main()
