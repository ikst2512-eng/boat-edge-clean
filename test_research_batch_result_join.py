import json
import tempfile
import unittest
from pathlib import Path
from research_batch_result_join import reconcile

class JoinTests(unittest.TestCase):
    def test_real_frozen_snapshots_with_four_known_results(self):
        root=Path(__file__).resolve().parent/"research_snapshots"
        results=[
            {"race_code":"202610270101","ticket":"3-4-1","status":"final","source_kind":"official"},
            {"race_code":"202610270102","ticket":"1-2-4","status":"final","source_kind":"official"},
            {"race_code":"202610270103","ticket":"3-6-4","status":"final","source_kind":"official"},
            {"race_code":"202610270104","ticket":"1-3-4","status":"final","source_kind":"official"}
        ]
        report=reconcile(root,results)
        self.assertEqual(report["counts"]["exploratory_matched"],4)
        self.assertEqual(report["counts"]["top1_hits"],1)
        self.assertEqual(report["counts"]["top3_hits"],1)
        self.assertEqual(report["counts"]["top10_hits"],1)
        self.assertEqual(report["eligible_formal"],0)
    def test_duplicate_results_all_excluded(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"202610270101.json"
            path.write_text(json.dumps({"race_code":"202610270101","status":"research",
                "validated":False,"predictions":["1-2-3"]*10}),encoding="utf-8")
            r={"race_code":"202610270101","ticket":"1-2-3","status":"final","source_kind":"official"}
            report=reconcile(d,[r,r])
            self.assertEqual(report["counts"].get("exploratory_matched",0),0)
            self.assertEqual(report["excluded"]["duplicate_result"],1)
if __name__=="__main__":unittest.main()
