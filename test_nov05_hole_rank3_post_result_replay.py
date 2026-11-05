"""Nov 5 post-result replay checks; no mock outcome is called prospective."""
import json
import tempfile
import unittest
from pathlib import Path

from nov05_hole_rank3_post_result_replay import run

CODE = "202611050101"
SHA = "a" * 40
BLOB = "b" * 40


def file_row(folder, code=CODE):
    return (f"100644 blob {BLOB}\t{folder}/{code}.json\0").encode()


class November5ReplayTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        path = self.root / "four_mode_forecasts"
        path.mkdir()
        self.forecast = path / (CODE + ".json")
        self.forecast.write_text(json.dumps({
            "schema": "CLEAN_FOUR_MODES_PREDEADLINE_V1",
            "race_code": CODE,
            "source_title_received_jst": "2026-11-05T09:01:00+09:00",
            "source_cards_received_jst": "2026-11-05T09:02:00+09:00",
            "generated_at_jst": "2026-11-05T09:03:00+09:00",
            "deadline_jst": "2026-11-05T15:20:00+09:00",
        }), encoding="utf-8")
        self.paths = file_row("four_mode_forecasts") + file_row("confirmed_results")
        self.snapshot = {
            "examined_main_sha": SHA,
            "intersection_race_codes": [CODE],
            "four_mode_original_files": 1,
            "clean_separate_original_files": 0,
            "status": "main_snapshot_research_comparable",
            "result_content_comparable_count": 1,
            "historical_topn_hits": {
                "hole": {"top1": 0, "top3": 0, "top5": 0, "top10": 0}
            },
        }
        self.scored = []

    def git(self, args):
        if args[:2] == ["rev-parse", "--verify"]:
            return (SHA + "\n").encode()
        if args[:3] == ["ls-tree", "-r", "-z"]:
            return self.paths
        raise AssertionError(args)

    def scorer(self, code, root):
        self.scored.append(code)
        return {"race_code": code, "status": "historical_comparison_only",
                "formal": False, "changed": True,
                "topn": {f"top{n}": {
                    "baseline": False, "candidate": True,
                    "gained": True, "lost": False
                } for n in (1, 3, 5, 10)}}

    def snapshot_checker(self, root, git):
        return self.snapshot

    def check(self, **kwargs):
        args = {"root": self.root, "git": self.git,
                "scorer": self.scorer,
                "snapshot_checker": self.snapshot_checker}
        args.update(kwargs)
        return run(**args)

    def test_same_race_baseline_and_candidate_reconciled_only_historically(self):
        report = self.check()
        self.assertEqual(report["status"], "retrospective_complete_not_prospective")
        self.assertEqual(report["forecast_original_count"], 1)
        self.assertEqual(report["comparable"], 1)
        self.assertEqual(report["topn"]["top10"]["baseline_hits"], 0)
        self.assertEqual(report["topn"]["top10"]["candidate_hits"], 1)
        self.assertEqual(report["topn"]["top10"]["gained"], 1)
        self.assertEqual(report["simulated_candidate_changed"], 1)
        self.assertEqual(report["prospective_enrolled_races"], None)
        self.assertEqual(report["formal_eligible_races"], None)
        self.assertFalse(report["pre_result_candidate_artifact_verified"])
        self.assertFalse(report["formal"])
        self.assertFalse(report["model_improvement_proven"])
        self.assertEqual(self.scored, [CODE])

    def test_missing_result_never_counted_as_loss(self):
        self.paths = file_row("four_mode_forecasts")
        self.snapshot.update({
            "intersection_race_codes": [],
            "status": "incomplete_saved_result_contents",
            "result_content_comparable_count": 0,
            "historical_topn_hits": None,
        })
        report = self.check()
        self.assertEqual(report["forecast_pending_result_filename"], 1)
        self.assertEqual(report["forecast_and_result_filename_pairs"], 0)
        self.assertIsNone(report["topn"])
        self.assertEqual(self.scored, [])
        self.assertFalse(report["formal"])

    def test_invalid_comparison_withholds_all_candidate_rates(self):
        def bad_score(code, root):
            self.scored.append(code)
            return {"race_code": code, "status": "invalid_result_or_timing",
                    "formal": False}
        report = self.check(scorer=bad_score)
        self.assertEqual(report["comparable"], 0)
        self.assertEqual(len(report["invalid_or_untrusted"]), 1)
        self.assertIsNone(report["topn"])
        self.assertFalse(report["prospective_validation"])

    def test_invalid_t12_excludes_before_scoring(self):
        data = json.loads(self.forecast.read_text())
        data["generated_at_jst"] = "2026-11-05T15:18:00+09:00"
        self.forecast.write_text(json.dumps(data), encoding="utf-8")
        report = self.check()
        self.assertEqual(report["local_source_t12_inconsistent_codes"], [CODE])
        self.assertEqual(self.scored, [])
        self.assertIsNone(report["topn"])

    def test_forged_main_sha_cannot_be_scored(self):
        def wrong_git(args):
            if args == ["rev-parse", "--verify", "refs/remotes/origin/main"]:
                return ("c" * 40 + "\n").encode()
            return self.git(args)
        with self.assertRaisesRegex(ValueError, "checked_out_main_ref_mismatch"):
            self.check(git=wrong_git)

    def test_unreconciled_hole_baseline_rejected(self):
        self.snapshot["historical_topn_hits"]["hole"]["top10"] = 1
        with self.assertRaisesRegex(ValueError, "four_mode_hole_baseline"):
            self.check()

    def test_different_snapshot_roster_rejected(self):
        self.snapshot["intersection_race_codes"] = ["202611050102"]
        with self.assertRaisesRegex(ValueError, "snapshot_roster_disagrees"):
            self.check()

    def test_bad_replay_result_does_not_break_siblings(self):
        self.paths += file_row("four_mode_forecasts", "202611050102")
        self.paths += file_row("confirmed_results", "202611050102")
        second = self.forecast.with_name("202611050102.json")
        extra = json.loads(self.forecast.read_text())
        extra["race_code"] = "202611050102"
        second.write_text(json.dumps(extra), encoding="utf-8")
        self.snapshot["four_mode_original_files"] = 2
        self.snapshot["intersection_race_codes"] = [CODE, "202611050102"]
        self.snapshot["result_content_comparable_count"] = 2

        def mixed(code, root):
            if code == CODE:
                return self.scorer(code, root)
            raise ValueError("broken_result")
        report = self.check(scorer=mixed)
        self.assertEqual(report["comparable"], 1)
        self.assertEqual(len(report["invalid_or_untrusted"]), 1)
        self.assertIsNone(report["topn"])
        self.assertEqual(self.scored, [CODE])


if __name__ == "__main__":
    unittest.main()
