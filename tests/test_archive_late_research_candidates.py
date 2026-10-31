import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from research_model import JST
from scripts.archive_late_research_candidates import archive


class ProspectiveCandidateArchiveTest(unittest.TestCase):
    def test_empty_upstream_candidates_distinct_from_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch("scripts.archive_late_research_candidates.build_candidates",return_value={"predictions":[]}):
                report=archive("20261031",Path(tmp),Path(tmp)/"out",datetime(2026,10,31,10,tzinfo=JST))
            self.assertEqual(report["upstream_candidate_count"],0)
            self.assertEqual(report["archive_state"],"no_valid_preview_pairs")
            self.assertEqual(report["saved_count"],0)


    def test_only_before_deadline_and_immutable(self):
        day="20261031"
        code="202610312311"
        record={"race_code":code,"predictions":["1-2-3"],"generated_from_received_at_jst":"2026-10-31T19:54:00+09:00",
                "status":"research_candidate_unvalidated"}
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            preview=root/"preview"
            folder=preview/day/"tkz"
            folder.mkdir(parents=True)
            (folder/(code+".json")).write_text(json.dumps({"source_row":{"締切時刻":"20:00"}}))
            out=root/"late"
            with patch("scripts.archive_late_research_candidates.build_candidates",
                       return_value={"predictions":[record]}):
                ontime=archive(day,preview,out,datetime(2026,10,31,19,56,tzinfo=JST))
                self.assertEqual(ontime["saved_count"],1)
                self.assertEqual(ontime["upstream_candidate_count"],1)
                self.assertEqual(ontime["archive_state"],"saved")
                path=out/day/(code+".json")
                initial=path.read_bytes()
                self.assertEqual(json.loads(initial)["generated_at_jst"],"2026-10-31T19:56:00+09:00")
                duplicate=archive(day,preview,out,datetime(2026,10,31,19,57,tzinfo=JST))
                self.assertEqual(duplicate["skipped"]["existing"],1)
                self.assertEqual(path.read_bytes(),initial)
                late=archive(day,preview,out,datetime(2026,10,31,19,58,tzinfo=JST))
                self.assertEqual(late["skipped"]["too_late"],1)
                self.assertEqual(path.read_bytes(),initial)

    def test_future_receipt_rejected(self):
        day="20261031"
        code="202610312311"
        record={"race_code":code,"predictions":["1-2-3"],"generated_from_received_at_jst":"2026-10-31T19:57:00+09:00"}
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            folder=root/day/"tkz"
            folder.mkdir(parents=True)
            (folder/(code+".json")).write_text(json.dumps({"source_row":{"締切時刻":"20:00"}}))
            with patch("scripts.archive_late_research_candidates.build_candidates",
                       return_value={"predictions":[record]}):
                result=archive(day,root,root/"out",datetime(2026,10,31,19,56,tzinfo=JST))
                self.assertEqual(result["skipped"]["invalid_source"],1)
                self.assertEqual(result["saved_count"],0)


if __name__=="__main__":
    unittest.main()
