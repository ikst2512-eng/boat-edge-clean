import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from research_model import JST
from clean_four_mode_capture import collect, publish_status

class CaptureEndToEndTests(unittest.TestCase):
    def test_research_archives_never_prove_production_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            result={"eligible_forecasts_today":156,"source_status":"available"}
            status=publish_status(result,root=Path(tmp),now=datetime(2026,11,2,8,0,tzinfo=JST))
            self.assertTrue(status["research_archives_present"])
            self.assertFalse(status["production_success_proven"])

    def test_published_predeadline_data_freezes_four_modes_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            now=datetime(2026,10,28,8,0,tzinfo=JST)
            code="202610280101"
            title={"レースコード":code,"電話投票締切予定":"12:00"}
            card={"レースコード":code,**{f"艇{i}_全国勝率":str(4+i*.3) for i in range(1,7)}}
            fetched=datetime(2026,10,28,7,30,tzinfo=JST)
            def read(url):
                return ([title] if "/title/" in url else [card],fetched,"a"*64)
            first=collect(root=root,now=now,read=read)
            self.assertEqual(first["new_saved"],[code])
            path=root/"four_mode_forecasts"/(code+".json")
            original=path.read_bytes()
            data=json.loads(original)
            self.assertEqual(set(data["modes"]),{"hit","balance","hole","narrow"})
            self.assertLess(data["generated_at_jst"],data["deadline_jst"])
            self.assertFalse(data["validated"])
            self.assertEqual(data["source_title_received_jst"],fetched.isoformat())
            self.assertEqual(data["source_cards_received_jst"],fetched.isoformat())
            second=collect(root=root,now=now,read=read)
            self.assertEqual(second["new_saved"],[])
            self.assertEqual(path.read_bytes(),original)

    def test_expired_race_is_not_backfilled(self):
        with tempfile.TemporaryDirectory() as tmp:
            now=datetime(2026,10,28,11,50,tzinfo=JST)
            code="202610280101"
            title={"レースコード":code,"電話投票締切予定":"12:00"}
            card={"レースコード":code,**{f"艇{i}_全国勝率":"5.0" for i in range(1,7)}}
            def read(url):
                return ([title] if "/title/" in url else [card],now,"a"*64)
            result=collect(root=Path(tmp),now=now,read=read)
            self.assertEqual(result["new_saved"],[])
            self.assertEqual(result["eligible_forecasts_today"],0)

if __name__=="__main__":unittest.main()
