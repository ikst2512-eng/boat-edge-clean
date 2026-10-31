import json
import tempfile
import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1] / 'scripts'))
from scripts.collect_live_preview_evidence import paired_six_lane_coverage


class PairedPreviewCoverageTests(unittest.TestCase):
    def test_only_same_race_complete_pairs_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            day="20261031"
            for kind, entries in {"tkz":[("202610310101","complete"),("202610310102","complete")],
                                  "stt":[("202610310101","complete"),("202610310102","incomplete"),
                                         ("202610310103","complete")]}.items():
                folder=root/day/kind
                folder.mkdir(parents=True)
                for code,status in entries:
                    (folder/(code+".json")).write_text(json.dumps({
                        "race_code":code,"kind":kind,"six_lane_validation":status,
                        "status":"late_preview_unvalidated_not_research_forecast"}))
            result=paired_six_lane_coverage(day,root)
            self.assertEqual(result["tkz_complete"],2)
            self.assertEqual(result["stt_complete"],2)
            self.assertEqual(result["paired_complete"],1)
            self.assertEqual(result["paired_codes"],["202610310101"])


if __name__=="__main__":
    unittest.main()
