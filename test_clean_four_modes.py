import unittest
from unittest.mock import patch
from datetime import datetime, timedelta
import clean_four_modes as model
from research_model import JST, probabilities


class CleanFourModeTests(unittest.TestCase):
    def test_independent_modes_and_targets(self):
        p=probabilities([6.2,5.1,4.2,4.5,3.1,2.9])
        result=model.rank_modes(p)
        self.assertEqual(set(result),{"hit","balance","hole","narrow"})
        self.assertEqual([result[n]["target_hit_rate_pct"] for n in ("hit","balance","hole","narrow")],[60,50,12.5,40])
        for mode in result.values():
            combos=[x["combo"] for x in mode["tickets"]]
            self.assertEqual(len(combos),len(set(combos)))
            self.assertTrue(all(len(x.split("-"))==3 for x in combos))
            self.assertIsNone(mode["actual_hit_rate_pct"])
        self.assertNotEqual(result["hit"]["tickets"],result["hole"]["tickets"])
        self.assertLessEqual(len(result["narrow"]["tickets"]),5)

    def test_optional_preview_not_required(self):
        import csv
        from io import StringIO
        today=datetime.now(JST)+timedelta(days=1)
        hd=today.strftime("%Y%m%d")
        code=hd+"0101"
        title=[{"レースコード":code,"電話投票締切予定":"23:59"}]
        card=[{"レースコード":code,**{f"艇{i}_全国勝率":str(4+i/10) for i in range(1,7)}}]
        def read(url):
            return (title if "/title/" in url else card,datetime.now(JST),"a"*64)
        with patch.object(model,"read_rows",side_effect=read):
            output=model.forecast(hd,"1","1")
        self.assertEqual(output["status"],"provisional")
        self.assertEqual(output["beforeinfo"],"not_required_when_unavailable")
        self.assertFalse(output["validated"])

    def test_refuse_invalid_race(self):
        with self.assertRaises(ValueError):
            model.forecast("20261028","99","1")


if __name__=="__main__":
    unittest.main()
