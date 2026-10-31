import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from scripts.evaluate_late_research_topn import evaluate


class HistoricalCliTest(unittest.TestCase):
    def test_historical_date_with_empty_archive_is_not_invented(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            run=subprocess.run([sys.executable,"-m","scripts.evaluate_late_research_topn",
                                "--day","20261031","--late-root",tmp],
                               capture_output=True,text=True,check=True)
            report=json.loads(run.stdout)
            self.assertEqual(report["date"],"20261031")
            self.assertEqual(report["paired_races"],0)
            self.assertEqual(sum(report["rejected"].values()),0)
            self.assertIsNone(report["topn"]["10"]["late_hit_rate_pct"])


class PairedTopNTest(unittest.TestCase):
    def test_same_race_result_and_prospective_times(self):
        day="20261031"
        code="202610310708"
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for directory in ("late","research_snapshots","confirmed_results"):
                (root/directory).mkdir()
            (root/"late"/day).mkdir()
            late={"race_code":code,"status":"research_candidate_unvalidated","research_only":True,
                  "generated_from_received_at_jst":"2026-10-31T17:00:00+09:00",
                  "generated_at_jst":"2026-10-31T17:01:00+09:00",
                  "race_deadline_jst":"2026-10-31T17:10:00+09:00",
                  "predictions":["1-2-3","1-2-4","1-2-5","1-2-6","1-3-2",
                                 "1-3-4","1-3-5","1-3-6","1-4-2","1-4-3"]}
            early={"race_code":code,"status":"research",
                   "generated_at":"2026-10-31T16:50:00+09:00",
                   "cutoff_jst":"2026-10-31T16:58:00+09:00",
                   "predictions":["1-2-4","1-2-5","1-2-6","1-3-4","1-3-5",
                                  "1-3-6","1-4-2","1-4-3","1-5-2","1-2-3"]}
            result={"race_code":code,"status":"confirmed","finish_order":[1,2,3]}
            (root/"late"/day/(code+".json")).write_text(json.dumps(late))
            (root/"research_snapshots"/(code+".json")).write_text(json.dumps(early))
            (root/"confirmed_results"/(code+".json")).write_text(json.dumps(result))
            report=evaluate(day,root/"late",root)
            self.assertEqual(report["paired_races"],1)
            self.assertEqual(report["topn"]["3"]["late_hits"],1)
            self.assertEqual(report["topn"]["3"]["early_hits"],0)
            self.assertEqual(report["topn"]["10"]["early_hits"],1)
            # Reject an early-baseline cutoff that was actually only T-5.
            early["cutoff_jst"]="2026-10-31T17:05:00+09:00"
            (root/"research_snapshots"/(code+".json")).write_text(json.dumps(early))
            self.assertEqual(evaluate(day,root/"late",root)["paired_races"],0)
            early["cutoff_jst"]="2026-10-31T16:58:00+09:00"
            (root/"research_snapshots"/(code+".json")).write_text(json.dumps(early))
            late["generated_at_jst"]="2026-10-31T17:09:00+09:00"
            (root/"late"/day/(code+".json")).write_text(json.dumps(late))
            rejected=evaluate(day,root/"late",root)
            self.assertEqual(rejected["paired_races"],0)
            self.assertEqual(rejected["rejected"]["outside_cutoff"],1)


if __name__=="__main__":
    unittest.main()
