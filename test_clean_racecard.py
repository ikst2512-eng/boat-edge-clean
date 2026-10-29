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
        with patch.object(clean_racecard,"read_rows",side_effect=read), patch.object(clean_racecard,"_fetch_preview",return_value=(None,{"status":"not_published_or_unavailable"})):
            result=clean_racecard.racecard(hd,"1","1")
        self.assertEqual(len(result["racers"]),6)
        self.assertEqual(result["racers"][0]["registration_no"],"4001")
        self.assertIsNone(result["beforeinfo"])
        self.assertEqual(result["meta"]["source"],"CLEAN_PUBLIC_PRE_RACE_CSV")


    def test_verified_preview_source(self):
        hd="20261030";code=hd+"0101"
        deadline=datetime.strptime(hd+"15:21","%Y%m%d%H:%M").replace(tzinfo=JST)
        def source(kind,path):
            row={"レースコード":code,"締切時刻":"15:21","取得日時":"2026-10-30T15:16:00+09:00"}
            for lane in range(1,7):
                p=f"艇{lane}_"
                row.update({p+"展示タイム":"6.80",p+"チルト":"0.0",
                            p+"コース":str(lane),p+"スタート展示":"0.12"})
            return [row],"b"*64
        with patch.object(clean_racecard,"_preview_rows",side_effect=source):
            preview,audit=clean_racecard._fetch_preview(code,"2026/10/30.csv",deadline)
        self.assertEqual(audit["status"],"ok")
        self.assertEqual(len(preview["racers"]),6)
        self.assertEqual(preview["start_exhibition"][0]["course"],1.0)

    def test_empty_exhibition_is_not_verified(self):
        hd="20261030";code=hd+"0101"
        deadline=datetime.strptime(hd+"15:21","%Y%m%d%H:%M").replace(tzinfo=JST)
        def blank(kind,path):
            row={"レースコード":code,"締切時刻":"15:21","取得日時":"2026-10-30T15:16:00+09:00"}
            for lane in range(1,7):
                prefix=f"艇{lane}_"
                row.update({prefix+"展示タイム":"",prefix+"チルト":"",
                            prefix+"コース":str(lane),prefix+"スタート展示":""})
            return [row],"f"*64
        with patch.object(clean_racecard,"_preview_rows",side_effect=blank):
            preview,audit=clean_racecard._fetch_preview(code,"2026/10/30.csv",deadline)
        self.assertIsNone(preview)
        self.assertEqual(audit["status"],"invalid_or_incomplete_exhibition")

    def test_missing_course_returns_invalid_without_crashing(self):
        hd="20261030";code=hd+"0101"
        deadline=datetime.strptime(hd+"15:21","%Y%m%d%H:%M").replace(tzinfo=JST)
        def partial(kind,path):
            row={"レースコード":code,"締切時刻":"15:21","取得日時":"2026-10-30T15:16:00+09:00"}
            for lane in range(1,7):
                prefix=f"艇{lane}_"
                row.update({prefix+"展示タイム":"6.80",prefix+"チルト":"0.0",
                            prefix+"コース":"" if lane==3 else str(lane),
                            prefix+"スタート展示":"0.12"})
            return [row],"e"*64
        with patch.object(clean_racecard,"_preview_rows",side_effect=partial):
            preview,audit=clean_racecard._fetch_preview(code,"2026/10/30.csv",deadline)
        self.assertIsNone(preview)
        self.assertEqual(audit["status"],"invalid_or_incomplete_exhibition")

    def test_late_preview_is_rejected(self):
        hd="20261030";code=hd+"0101"
        deadline=datetime.strptime(hd+"15:21","%Y%m%d%H:%M").replace(tzinfo=JST)
        with patch.object(clean_racecard,"_preview_rows",return_value=([{
            "レースコード":code,"締切時刻":"15:21",
            "取得日時":"2026-10-30T15:22:00+09:00"}],"c"*64)):
            preview,audit=clean_racecard._fetch_preview(code,"2026/10/30.csv",deadline)
        self.assertIsNone(preview)
        self.assertNotEqual(audit["status"],"ok")

    def test_race_identity_never_accepts_other_races(self):
        hd="20261030";code=hd+"0101"
        deadline=datetime.strptime(hd+"15:21","%Y%m%d%H:%M").replace(tzinfo=JST)
        def unrelated(kind,path):
            row={"レースコード":"202610300102","締切時刻":"15:21",
                 "取得日時":"2026-10-30T15:16:00+09:00"}
            for lane in range(1,7):
                prefix=f"艇{lane}_"
                row.update({prefix+"展示タイム":"6.80",prefix+"チルト":"0.0",
                            prefix+"コース":str(lane),prefix+"スタート展示":"0.12"})
            return [row],"9"*64
        with patch.object(clean_racecard,"_preview_rows",side_effect=unrelated):
            preview,audit=clean_racecard._fetch_preview(code,"2026/10/30.csv",deadline)
        self.assertIsNone(preview)
        self.assertNotEqual(audit["status"],"ok")

    def test_direct_origin_used_before_daily_csv_publication(self):
        hd=(datetime.now(JST)+timedelta(days=1)).strftime("%Y%m%d")
        code=hd+"0101"
        title=[{"レースコード":code,"電話投票締切予定":"23:59"}]
        row={"レースコード":code}
        for lane in range(1,7):
            row.update({f"艇{lane}_登録番号":str(4000+lane),f"艇{lane}_選手名":"選手",
                        f"艇{lane}_級別":"A1"})
        with patch.object(clean_racecard,"read_rows",side_effect=ValueError("source unavailable")), \\
             patch("clean_direct_sources.holding_rows",return_value=(title,datetime.now(JST),"a"*64)), \\
             patch("clean_direct_sources.fetch_bytes",return_value=b"direct"), \\
             patch("clean_direct_sources.parse_card",return_value=row), \\
             patch.object(clean_racecard,"_fetch_preview",return_value=(None,{"status":"not_published_or_unavailable"})):
            result=clean_racecard.racecard(hd,"1","1")
        self.assertEqual(result["meta"]["source"],"CLEAN_DIRECT_PRE_RACE")
        self.assertEqual(len(result["racers"]),6)

    def test_bad_venue(self):
        with self.assertRaises(ValueError):
            clean_racecard.racecard("20261028","99","1")

if __name__=="__main__":unittest.main()
