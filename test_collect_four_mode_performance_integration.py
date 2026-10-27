"""End-to-end scoring fixture: only pre-race archive plus confirmed outcome and payout may count."""
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from collect_four_mode_performance import run
from research_model import JST

class VerifiedFourModeIntegrationTests(unittest.TestCase):
    def test_verified_result_flows_to_all_budget_reports(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            code="202610280101"
            (root/"four_mode_forecasts").mkdir()
            (root/"confirmed_results").mkdir()
            archive={"schema":"CLEAN_FOUR_MODES_PREDEADLINE_V1","race_code":code,
                     "generated_at_jst":"2026-10-28T08:00:00+09:00",
                     "deadline_jst":"2026-10-28T12:00:00+09:00",
                     "modes":{k:{"tickets":[{"combo":"1-2-3"},{"combo":"2-1-3"}]}
                              for k in ("hit","balance","hole","narrow")}}
            (root/"four_mode_forecasts"/(code+".json")).write_text(json.dumps(archive),encoding="utf-8")
            result={"race_code":code,"status":"confirmed","finish_order":[1,2,3],
                    "source_url":"https://example.org/official.csv",
                    "confirmed_at_jst":"2026-10-28T12:20:00+09:00"}
            (root/"confirmed_results"/(code+".json")).write_text(json.dumps(result),encoding="utf-8")
            proof=lambda path,deadline:"audited-first-add"
            payout=lambda race,winning:2400
            now=datetime(2026,10,28,13,0,tzinfo=JST)
            for budget in (5000,10000):
                output=run(root,budget,payout,proof,now)
                self.assertEqual(output["counts"]["complete"],1)
                self.assertEqual(output["modes"]["hit"]["sample_races"],1)
                self.assertEqual(output["modes"]["hit"]["actual_hit_rate_pct"],100.0)
                self.assertEqual(output["modes"]["hit"]["actual_roi_pct"],1200.0)
                self.assertEqual(output["modes"]["hit"]["invested_yen"],budget)
            detail=json.loads((root/"four_mode_performance/verified_races"/(code+".json")).read_text())
            self.assertEqual(detail["first_git_sha"],"audited-first-add")
            self.assertEqual(detail["official_payout_yen_per_100"],2400)

    def test_never_score_missing_result_or_unverified_archive(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/"four_mode_forecasts").mkdir()
            code="202610280101"
            archive={"race_code":code,"deadline_jst":"2026-10-28T12:00:00+09:00"}
            (root/"four_mode_forecasts"/(code+".json")).write_text(json.dumps(archive))
            now=datetime(2026,10,28,13,0,tzinfo=JST)
            output=run(root,5000,lambda *_:2400,lambda *_:"proof",now)
            self.assertEqual(output["counts"]["overdue_result"],1)
            self.assertIsNone(output["modes"]["hit"]["actual_roi_pct"])
            output=run(root,5000,lambda *_:2400,lambda *_:(_ for _ in ()).throw(ValueError("late")),now)
            self.assertEqual(output["counts"]["unverified"],1)
            self.assertEqual(output["counts"]["complete"],0)

if __name__=="__main__":unittest.main()
