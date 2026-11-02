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

    def test_next_day_capture_preserves_yesterday_and_rejects_replays(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            def source_for(day):
                code=day+"0101"
                title={"レースコード":code,"電話投票締切予定":"12:00"}
                card={"レースコード":code,**{f"艇{i}_全国勝率":str(4+i*.3) for i in range(1,7)}}
                received=datetime.strptime(day+"0730","%Y%m%d%H%M").replace(tzinfo=JST)
                def read(url):
                    return ([title] if "/title/" in url else [card],received,"a"*64)
                return code,read
            old_code,old_read=source_for("20261102")
            new_code,new_read=source_for("20261103")
            old_now=datetime(2026,11,2,8,0,tzinfo=JST)
            new_now=datetime(2026,11,3,8,0,tzinfo=JST)
            self.assertEqual(collect(root=root,now=old_now,read=old_read)["new_saved"],[old_code])
            old_path=root/"four_mode_forecasts"/(old_code+".json")
            old_bytes=old_path.read_bytes()
            self.assertEqual(collect(root=root,now=new_now,read=new_read)["new_saved"],[new_code])
            new_path=root/"four_mode_forecasts"/(new_code+".json")
            new_bytes=new_path.read_bytes()
            self.assertEqual(collect(root=root,now=new_now,read=new_read)["new_saved"],[])
            self.assertEqual(old_path.read_bytes(),old_bytes)
            self.assertEqual(new_path.read_bytes(),new_bytes)
            self.assertEqual(json.loads(new_bytes)["race_code"],new_code)

    def test_source_receipt_after_generation_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            now=datetime(2026,10,28,8,0,tzinfo=JST)
            later=datetime(2026,10,28,8,0,1,tzinfo=JST)
            code="202610280101"
            title={"レースコード":code,"電話投票締切予定":"12:00"}
            card={"レースコード":code,**{f"艇{i}_全国勝率":"5.0" for i in range(1,7)}}
            def read(url):
                return ([title] if "/title/" in url else [card],later,"a"*64)
            result=collect(root=root,now=now,read=read)
            self.assertEqual(result["new_saved"],[])
            self.assertEqual(result["excluded"].get("source_receipt_after_generation"),1)
            self.assertFalse((root/"four_mode_forecasts"/(code+".json")).exists())

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
