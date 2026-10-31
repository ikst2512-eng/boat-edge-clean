"""Regression: research lane-one cohorts must only count valid pre-race evidence."""
import json
import tempfile
import unittest
from pathlib import Path
from scripts.research_prerace_feature_audit import analyze


class LaneFeatureEvidenceTests(unittest.TestCase):
    def test_invalid_deadlines_and_finishes_excluded(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/"research_snapshots").mkdir()
            (root/"confirmed_results").mkdir()
            tickets=["1-2-3","1-3-2","2-1-3","2-3-1","3-1-2",
                     "3-2-1","1-2-4","1-4-2","4-1-2","4-2-1"]
            entries=[
                ("202610300101","2026-10-30T10:00:00+09:00",[1,2,3]),
                ("202610300102","2026-10-30T10:35:00+09:00",[1,2,3]),
                ("202610300103","2026-10-30T10:00:00",[1,2,3]),
                ("202610300104","2026-10-30T10:00:00+09:00",[1,1,2]),
            ]
            for code,generated,finish in entries:
                forecast={"race_code":code,"status":"research","generated_at":generated,
                          "cutoff_jst":"2026-10-30T10:30:00+09:00",
                          "source_deadline_jst":"2026-10-30T10:42:00+09:00",
                          "national_win_rates":[6,5,4,3,2,1],"predictions":tickets}
                result={"race_code":code,"status":"confirmed","finish_order":finish}
                (root/"research_snapshots"/(code+".json")).write_text(json.dumps(forecast))
                (root/"confirmed_results"/(code+".json")).write_text(json.dumps(result))
            audit=analyze(root)
            self.assertEqual(audit["cohorts"]["holdout"]["all"]["n"],1)
            self.assertEqual(audit["cohorts"]["holdout"]["all"]["top10"],1)
            self.assertEqual(audit["rejected"],3)


if __name__=="__main__":
    unittest.main()
