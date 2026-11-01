import json
import tempfile
import unittest
from pathlib import Path
from research_prospective_miss_report import report


class ProspectiveMissReportTest(unittest.TestCase):
    def test_shared_verified_cohort_and_result_disagreement(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for directory in ("prospective_predictions", "confirmed_results"):
                (root / directory).mkdir()
            code = "202610300101"
            tickets = ["1-2-3", "1-3-2", "2-1-3", "1-2-4", "2-3-1",
                       "1-4-2", "3-1-2", "2-1-4", "3-2-1", "1-5-2"]
            (root / "prospective_predictions" / (code + ".json")).write_text(
                json.dumps({"race_code": code, "predictions": tickets,
                            "source_deadline_jst": "2026-10-30T09:22:00+09:00",
                            "cutoff_jst": "2026-10-30T09:10:00+09:00",
                            "generated_at": "2026-10-30T09:03:00+09:00",
                            "source_title_received_jst": "2026-10-30T09:01:00+09:00",
                            "source_cards_received_jst": "2026-10-30T09:02:00+09:00"}))
            result = root / "confirmed_results" / (code + ".json")
            result.write_text(json.dumps({"race_code": code, "status": "confirmed", "finish_order": [1, 2, 4]}))
            def scorer(c, r):
                return {"race_code": c, "status": "evaluated", "audited": True,
                        "formal": False, "scoring_kind": "prospective_research_only",
                        "first_add_sha": "test-sha", "winning_ticket": "1-2-4",
                        "rank": 4, "top3": False, "top5": True, "top10": True}
            good = report("20261030", root, scorer=scorer)
            self.assertEqual(good["counts"]["evaluated"], 1)
            self.assertEqual([good["topn"][f"top{n}"]["hits"] for n in (3, 5, 10)], [0, 1, 1])
            self.assertEqual(good["topn"]["top3"]["third_place_uncovered_given_first_second"], 1)
            result.write_text(json.dumps({"race_code": code, "status": "confirmed", "finish_order": [1, 2, 5]}))
            rejected = report("20261030", root, scorer=scorer)
            self.assertEqual(rejected["counts"]["audit_rejected"], 1)
            self.assertEqual(rejected["topn"]["top10"]["evaluated"], 0)
            self.assertFalse(rejected["formal"])
            self.assertFalse(rejected["remote_first_seen_verified"])
            # Existing archive has a known ordering defect: receipt after generation.
            archive = root / "prospective_predictions" / (code + ".json")
            original = json.loads(archive.read_text())
            archive.write_text(json.dumps({**original, "generated_at": "2026-10-30T09:00:00+09:00"}))
            time_rejected = report("20261030", root, scorer=scorer)
            self.assertEqual(time_rejected["counts"]["audit_rejected"], 1)
            self.assertEqual(time_rejected["counts"]["evaluated"], 0)
            archive.write_text(json.dumps(original))

            def pending(c, r):
                return {"race_code": c, "status": "result_unavailable",
                        "audited": True, "formal": False,
                        "scoring_kind": "prospective_research_only"}
            pending_report = report("20261030", root, scorer=pending)
            self.assertEqual(pending_report["counts"]["awaiting_result"], 1)
            self.assertEqual(pending_report["counts"]["evaluated"], 0)
            archive.write_text(json.dumps({**original, "generated_at": "2026-10-30T09:00:00+09:00"}))
            invalid_pending = report("20261030", root, scorer=pending)
            self.assertEqual(invalid_pending["counts"]["audit_rejected"], 1)
            self.assertEqual(invalid_pending["counts"]["awaiting_result"], 0)
            archive.write_text(json.dumps(original))
            def fake_pending(c, r):
                return {"race_code": c, "status": "result_unavailable", "audited": False,
                        "formal": False, "scoring_kind": "prospective_research_only"}
            fake_report = report("20261030", root, scorer=fake_pending)
            self.assertEqual(fake_report["counts"]["audit_rejected"], 1)
            self.assertEqual(fake_report["counts"]["awaiting_result"], 0)


if __name__ == "__main__":
    unittest.main()
