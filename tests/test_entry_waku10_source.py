import csv
import io
import unittest
from datetime import datetime, timezone, timedelta
from entry_waku10_source import fetch_waku10,extract_waku10_course_evidence

JST=timezone(timedelta(hours=9))
NOW="2026-11-03T18:29:00+09:00"
CODE="202611030101"
NAMES=["田中 堅","山口 修路","吉永 泰弘","大谷 健太","吉島 祥之","磯村 匠"]
REGS=["4491","4367","3710","4836","4215","4641"]
def card():
    return {"race_key":"20261103-01-01","racers":[
        {"lane":i,"name":name,"registration_no":reg}
        for i,(name,reg) in enumerate(zip(NAMES,REGS),1)]}
def waku():
    row={"レースコード":CODE}
    for lane in range(1,7):
        row[f"艇{lane}_選手名"]=NAMES[lane-1]
        row[f"艇{lane}_枠番別平均ST"]="0.16"
        for slot in range(1,11):
            p=f"艇{lane}_過去{slot}走_"
            row[p+"着順"]=str((slot%6)+1)
            row[p+"進入"]="" if slot!=10 or lane in (1,2,4) else str(lane+1 if lane<6 else 5)
    return row
def source(row=None):
    return {"race_code":CODE,"research_only":True,"official_source_verified":False,
            "received_at":"2026-11-03T18:28:00+09:00",
            "sha256":"a"*64,"row":row or waku()}
def encode(row):
    file=io.StringIO(); writer=csv.DictWriter(file,fieldnames=list(row))
    writer.writeheader();writer.writerow(row)
    return file.getvalue().encode("utf-8-sig")

class Waku10SourceTests(unittest.TestCase):
    def test_published_nov3_shape_10_10_9_10_9_9_at_matching_courses(self):
        report=extract_waku10_course_evidence(card(),source(),[1,2,3,4,5,6],
                                                frozen_at=NOW,min_course_starts=8)
        self.assertEqual([r["matchedCourseCompletedRuns"] for r in report["rows"]],
                         [10,10,9,10,9,9])
        self.assertTrue(report["all_course_samples_sufficient"])
        self.assertTrue(report["frame_st_is_not_course_st"])
        self.assertTrue(all(r["courseAverageST"] is None for r in report["rows"]))
        self.assertTrue(all(r["frameAverageSTProxy"]==0.16 for r in report["rows"]))
        self.assertFalse(report["formal_forecast_approved"])
    def test_mismatched_actual_entry_fails_sample_instead_of_faking_course_counts(self):
        report=extract_waku10_course_evidence(card(),source(),[2,1,3,4,5,6],
                                                frozen_at=NOW,min_course_starts=8)
        self.assertEqual(report["rows"][0]["matchedCourseCompletedRuns"],0)
        self.assertEqual(report["rows"][1]["matchedCourseCompletedRuns"],0)
        self.assertFalse(report["all_course_samples_sufficient"])
    def test_no_name_matching_means_no_player_mapping(self):
        item=waku();item["艇4_選手名"]="別人"
        with self.assertRaisesRegex(ValueError,"identity_mismatch"):
            extract_waku10_course_evidence(card(),source(item),[1,2,3,4,5,6],frozen_at=NOW)
    def test_source_not_published_at_freeze_rejected(self):
        evidence=source(); evidence["received_at"]="2026-11-03T18:30:00+09:00"
        with self.assertRaisesRegex(ValueError,"source_after_freeze"):
            extract_waku10_course_evidence(card(),evidence,[1,2,3,4,5,6],frozen_at=NOW)
    def test_f_marks_are_not_fake_finishes(self):
        item=waku();item["艇1_過去1走_着順"]="F"
        report=extract_waku10_course_evidence(card(),source(item),[1,2,3,4,5,6],frozen_at=NOW)
        self.assertEqual(report["rows"][0]["matchedCourseCompletedRuns"],9)
        self.assertTrue(report["rows"][0]["sufficient_sample"])
    def test_fetch_exact_race_and_sha_before_cutoff(self):
        item=waku()
        got=fetch_waku10(CODE,cutoff_at="2026-11-03T18:31:00+09:00",
                         fetch=lambda url:encode(item),
                         clock=lambda:datetime(2026,11,3,18,28,tzinfo=JST))
        self.assertEqual(got["row"]["レースコード"],CODE)
        self.assertEqual(len(got["sha256"]),64)
        self.assertIn("/2026/11/03.csv",got["source_url"])
    def test_fetch_after_cutoff_fails_without_network(self):
        with self.assertRaisesRegex(ValueError,"requested_after_cutoff"):
            fetch_waku10(CODE,cutoff_at="2026-11-03T18:31:00+09:00",
                         fetch=lambda url:self.fail("unexpected fetch"),
                         clock=lambda:datetime(2026,11,3,18,32,tzinfo=JST))
    def test_duplicate_source_race_is_rejected(self):
        original=encode(waku())
        with self.assertRaisesRegex(ValueError,"duplicate_race"):
            fetch_waku10(CODE,cutoff_at="2026-11-03T18:31:00+09:00",
                         fetch=lambda url:original+original.split(b"\\n",1)[1],
                         clock=lambda:datetime(2026,11,3,18,28,tzinfo=JST))
if __name__=="__main__":unittest.main()
