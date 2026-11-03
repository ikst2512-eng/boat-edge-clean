import json
import tempfile
import unittest
from unittest.mock import patch

# New captures must be distinguishable from immutable V1 archives.

from datetime import datetime
from pathlib import Path
from research_model import JST
from clean_four_mode_capture import collect, publish_status

class CaptureEndToEndTests(unittest.TestCase):
    def test_capture_outcome_never_implies_remote_publication(self):
        from clean_four_mode_capture import classify_capture
        cases = (
            ({"source_status": "source_incomplete"}, "source_unavailable"),
            ({"source_status": "available", "new_saved": ["202611030101"]}, "generated_locally_unpublished"),
            ({"source_status": "available", "already_saved": 2}, "no_new_already_saved"),
            ({"source_status": "available", "cutoff_skipped": 2}, "no_new_cutoff_skipped"),
            ({"source_status": "available", "excluded": {"missing_race_card": 1}}, "no_new_invalid_candidates"),
            ({"source_status": "available"}, "no_new_candidates"),
        )
        for value, expected in cases:
            with self.subTest(expected=expected):
                self.assertEqual(classify_capture(value), expected)
                with tempfile.TemporaryDirectory() as tmp:
                    status = publish_status(value, root=Path(tmp), now=datetime(2026,11,3,8,0,tzinfo=JST))
                    self.assertEqual(status["capture_outcome"], expected)
                    self.assertFalse(status["production_success_proven"])

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
            self.assertEqual(data["model_version"],"CLEAN_FOUR_MODES_V2_PROVISIONAL_UNCALIBRATED")
            self.assertEqual([len(data["modes"][m]["tickets"]) for m in ("narrow","hit","balance","hole")],[5,10,16,22])
            self.assertTrue(all(data["modes"][m]["count_policy"]=="provisional_new_generation_v2" for m in data["modes"]))
            self.assertLess(data["generated_at_jst"],data["deadline_jst"])
            self.assertFalse(data["validated"])
            self.assertEqual(data["source_title_received_jst"],fetched.isoformat())
            self.assertEqual(data["source_cards_received_jst"],fetched.isoformat())
            second=collect(root=root,now=now,read=read)
            self.assertEqual(second["new_saved"],[])
            self.assertEqual(second["already_saved"],1)
            self.assertEqual(second["cutoff_skipped"],0)
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

    def test_already_frozen_after_cutoff_not_miscounted_as_missed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            code="202611030101"
            title={"レースコード":code,"電話投票締切予定":"12:00"}
            card={"レースコード":code,**{f"艇{i}_全国勝率":"5.0" for i in range(1,7)}}
            receipt=datetime(2026,11,3,7,30,tzinfo=JST)
            def read(url):
                return ([title] if "/title/" in url else [card],receipt,"a"*64)
            first=collect(root=root,now=datetime(2026,11,3,8,0,tzinfo=JST),read=read)
            self.assertEqual(first["new_saved"],[code])
            saved=root/"four_mode_forecasts"/(code+".json")
            original=saved.read_bytes()
            later=collect(root=root,now=datetime(2026,11,3,13,0,tzinfo=JST),read=read)
            self.assertEqual(later["new_saved"],[])
            self.assertEqual(later["already_saved"],1)
            self.assertEqual(later["cutoff_skipped"],0)
            self.assertEqual(saved.read_bytes(),original)
            status=publish_status(later,root=root,now=datetime(2026,11,3,13,0,tzinfo=JST))
            self.assertEqual(status["already_saved"],1)
            self.assertEqual(status["cutoff_skipped"],0)

    def test_empty_daily_titles_recover_from_direct_pre_race_holding(self):
        with tempfile.TemporaryDirectory() as tmp:
            now=datetime(2026,11,4,8,0,tzinfo=JST)
            code="202611040101"
            title={"レースコード":code,"電話投票締切予定":"12:00"}
            card={"レースコード":code,**{
                f"艇{i}_全国勝率":"5.0" for i in range(1,7)}}
            received=datetime(2026,11,4,7,30,tzinfo=JST)
            def read(url):
                return ([] if "/title/" in url else [card],received,"a"*64)
            with patch("clean_direct_sources.holding_rows",
                       return_value=([title],received,"b"*64)), patch(
                           "clean_direct_sources.direct_cards") as fetch_cards:
                result=collect(root=Path(tmp),now=now,read=read)
            fetch_cards.assert_not_called()
            self.assertEqual(result["new_saved"],[code])
            self.assertEqual(result["source_probes"]["title_direct"]["status"],
                             "available")
            original=json.loads((Path(tmp)/"four_mode_forecasts"/(code+".json")).read_text())
            self.assertEqual(original["source_sha256"]["title"],"b"*64)
            self.assertEqual(original["source_sha256"]["race_cards"],"a"*64)

    def test_empty_daily_cards_recover_from_direct_pre_race_cards(self):
        with tempfile.TemporaryDirectory() as tmp:
            now=datetime(2026,11,4,8,0,tzinfo=JST)
            code="202611040101"
            title={"レースコード":code,"電話投票締切予定":"12:00"}
            card={"レースコード":code,**{
                f"艇{i}_全国勝率":"5.0" for i in range(1,7)}}
            received=datetime(2026,11,4,7,30,tzinfo=JST)
            def read(url):
                return ([title] if "/title/" in url else [],received,"a"*64)
            with patch("clean_direct_sources.direct_cards",
                       return_value=([card],received,"b"*64,
                                     {code:"c"*64},{})):
                result=collect(root=Path(tmp),now=now,read=read)
            self.assertEqual(result["new_saved"],[code])
            self.assertEqual(result["source_probes"]["race_cards_direct"]["status"],
                             "available")
            saved=json.loads((Path(tmp)/"four_mode_forecasts"/(code+".json")).read_text())
            self.assertEqual(saved["source_sha256"]["race_cards"],"c"*64)

    def test_empty_daily_sources_recover_only_from_complete_alternate_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            now=datetime(2026,11,4,8,0,tzinfo=JST)
            code="202611040101"
            title={"レースコード":code,"電話投票締切予定":"12:00"}
            card={"レースコード":code,**{
                f"艇{i}_全国勝率":"5.0" for i in range(1,7)}}
            received=datetime(2026,11,4,7,30,tzinfo=JST)
            def read(url):return ([],received,"a"*64)
            with patch("clean_direct_sources.holding_rows",
                       side_effect=ValueError("holding unavailable")), patch(
                           "clean_openapi_sources.load",
                           return_value=([title],[card],received,"b"*64,
                                         {"source":"nonofficial_openapi_v1"})):
                result=collect(root=Path(tmp),now=now,read=read)
            self.assertEqual(result["new_saved"],[code])
            self.assertEqual(result["source_probes"]["openapi_direct"]["status"],
                             "available")
            saved=json.loads((Path(tmp)/"four_mode_forecasts"/(code+".json")).read_text())
            self.assertEqual(saved["source_sha256"],
                             {"title":"b"*64,"race_cards":"b"*64})

    def test_empty_titles_with_available_cards_are_not_healthy(self):
        with tempfile.TemporaryDirectory() as tmp:
            now=datetime(2026,11,3,8,0,tzinfo=JST)
            card={"レースコード":"202611030101",**{f"艇{i}_全国勝率":"5.0" for i in range(1,7)}}
            def read(url):
                return ([] if "/title/" in url else [card],now,"a"*64)
            with patch("clean_direct_sources.holding_rows",
                       side_effect=ValueError("holding unavailable")), patch(
                           "clean_openapi_sources.load",
                           side_effect=ValueError("alternate unavailable")):
                result=collect(root=Path(tmp),now=now,read=read)
            self.assertEqual(result["source_status"],"empty_titles")
            self.assertEqual(result["new_saved"],[])
            self.assertEqual(result["published_card_rows"],1)
            self.assertEqual(result["published_title_rows"],0)
            status=publish_status(result,root=Path(tmp),now=now)
            self.assertEqual(status["source_status"],"empty_titles")

    def test_invalid_national_win_rates_are_excluded_without_archive(self):
        for bad in ("nan", "inf", "-inf", "-1", "10.01", "100"):
            with self.subTest(bad=bad), tempfile.TemporaryDirectory() as tmp:
                code="202611030101"
                now=datetime(2026,11,3,8,0,tzinfo=JST)
                receipt=datetime(2026,11,3,7,30,tzinfo=JST)
                title={"レースコード":code,"電話投票締切予定":"12:00"}
                card={"レースコード":code,**{f"艇{i}_全国勝率":"5.0" for i in range(1,7)}}
                card["艇1_全国勝率"]=bad
                def read(url):
                    return ([title] if "/title/" in url else [card],receipt,"a"*64)
                result=collect(root=Path(tmp),now=now,read=read)
                self.assertEqual(result["new_saved"],[])
                self.assertEqual(result["excluded"].get("invalid_national_win_rate"),1)
                self.assertEqual(result["excluded_races"],
                                 [{"race_code": code, "reason": "invalid_national_win_rate"}])
                state=publish_status(result,root=Path(tmp),now=now)
                self.assertEqual(state["excluded_races"], result["excluded_races"])
                self.assertFalse((Path(tmp)/"four_mode_forecasts"/(code+".json")).exists())

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
