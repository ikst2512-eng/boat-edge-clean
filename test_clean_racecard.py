import unittest
from datetime import datetime,timedelta
from unittest.mock import patch
import clean_racecard
from research_model import JST

class CleanRacecardTests(unittest.TestCase):
    def test_six_lanes_without_legacy_and_optional_preview(self):
        hd=(datetime.now(JST)+timedelta(days=1)).strftime("%Y%m%d")
        code=hd+"0101"
        title=[{"レースコード":code,"電話投票締切予定":"23:59"}]
        row={"レースコード":code}
        for i in range(1,7):
            p=f"艇{i}_"
            row.update({p+"登録番号":str(4000+i),p+"選手名":f"選手{i}",
                        p+"級別":"A1",p+"全国勝率":"5.5",
                        p+"全国2連対率":"40",p+"全国3連対率":"60",
                        p+"当地勝率":"4.7",p+"全国平均ST":"0.15",
                        p+"モーター番号":"12",p+"ボート番号":"25"})
        def read(url):
            return (title if "/title/" in url else [row],datetime.now(JST),"a"*64)
        with patch.object(clean_racecard,"read_rows",side_effect=read):
            result=clean_racecard.racecard(hd,"1","1")
        self.assertEqual(len(result["racers"]),6)
        self.assertEqual(result["racers"][0]["registration_no"],"4001")
        self.assertIsNone(result["beforeinfo"])
        self.assertEqual(result["meta"]["source"],"CLEAN_PUBLIC_PRE_RACE_CSV")

    def test_bad_venue(self):
        with self.assertRaises(ValueError):
            clean_racecard.racecard("20261028","99","1")

if __name__=="__main__":unittest.main()
