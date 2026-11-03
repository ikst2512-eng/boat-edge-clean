import csv
import io
import json
import tempfile
import unittest
from datetime import datetime,timezone,timedelta
from pathlib import Path
from entry_waku10_score import evaluate_waku10_archives
from test_entry_waku10_durable_ledger import sample,raw

JST=timezone(timedelta(hours=9))
DAY="20261103"
NOW=datetime(2026,11,3,23,30,tzinfo=JST)

def make_source(*, result_ticket=None, result_time="2026-11-03T18:47:00+09:00",duplicate=False):
    ticket=(result_ticket or sample()["baseline"][0]).split("-")
    row={"レースコード":"202611030708","取得日時":result_time,
         "1着_艇番":ticket[0],"2着_艇番":ticket[1],"3着_艇番":ticket[2]}
    f=io.StringIO(); w=csv.DictWriter(f,fieldnames=list(row))
    w.writeheader();w.writerow(row)
    if duplicate:w.writerow(row)
    return f.getvalue().encode("utf-8-sig")

def write_sample(root, *,data=None):
    dir=Path(root)/"waku10"/DAY;dir.mkdir(parents=True,exist_ok=True)
    (dir/"202611030708.json").write_bytes(data or raw(sample()))

class MatchedScoreTests(unittest.TestCase):
    def test_one_matched_cohort_topn_three_models(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_sample(tmp)
            out=evaluate_waku10_archives(tmp,DAY,result_fetch=lambda url:make_source(),
                                         clock=lambda:NOW)
            self.assertEqual(out["paired_races"],1)
            self.assertEqual(out["topn"]["baseline"]["Top3"]["hits"],1)
            self.assertEqual(out["topn"]["baseline"]["Top3"]["races"],1)
            self.assertEqual(out["topn"]["waku10_course"]["Top5"]["races"],1)
            self.assertEqual(out["topn"]["waku10_course_plus_frame_st_proxy"]["Top10"]["races"],1)
            self.assertFalse(out["forward_date_separated"])
            self.assertFalse(out["independent_holdout_verified"])
            self.assertFalse(out["model_accuracy_improvement_proven"])
            self.assertFalse(out["production_forecast_changed"])
    def test_source_result_not_after_cutoff_is_excluded_not_a_miss(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_sample(tmp)
            out=evaluate_waku10_archives(tmp,DAY,
                result_fetch=lambda url:make_source(result_time="2026-11-03T18:30:00+09:00"),
                clock=lambda:NOW)
            self.assertEqual(out["paired_races"],0)
            self.assertEqual(out["excluded"]["result_not_post_cutoff"],1)
            self.assertIsNone(out["topn"]["baseline"]["Top3"]["hit_rate"])
    def test_duplicate_result_race_is_excluded_from_all_arms(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_sample(tmp)
            out=evaluate_waku10_archives(tmp,DAY,
                result_fetch=lambda url:make_source(duplicate=True),clock=lambda:NOW)
            self.assertEqual(out["paired_races"],0)
            self.assertEqual(out["excluded"]["result_unavailable"],1)
            self.assertEqual(out["result_source_receipt"]["duplicate_race_codes"],1)
    def test_missing_result_is_not_scored_as_loss(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_sample(tmp)
            content=make_source().replace(b"202611030708",b"202611030709")
            out=evaluate_waku10_archives(tmp,DAY,result_fetch=lambda url:content,
                                         clock=lambda:NOW)
            self.assertEqual(out["paired_races"],0)
            self.assertEqual(out["excluded"]["result_unavailable"],1)
    def test_no_archives_does_not_request_results_or_make_up_accuracy(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=evaluate_waku10_archives(tmp,DAY,
                result_fetch=lambda url:self.fail("No archive; no result fetch"),clock=lambda:NOW)
            self.assertEqual(out["paired_races"],0)
            self.assertIsNone(out["result_source_receipt"])
            self.assertIsNone(out["topn"]["baseline"]["Top10"]["hit_rate"])
    def test_mutated_capture_never_enters_denominator(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=sample();p["frame_st_is_not_course_st"]=False
            write_sample(tmp,data=raw(p))
            out=evaluate_waku10_archives(tmp,DAY,
                result_fetch=lambda url:self.fail("invalid archive"),clock=lambda:NOW)
            self.assertEqual(out["paired_races"],0)
            self.assertEqual(out["excluded"]["invalid_or_unverified_archive"],1)
if __name__=="__main__":unittest.main()
