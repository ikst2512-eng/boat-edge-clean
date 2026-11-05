import json
import tempfile
import unittest
from pathlib import Path

from nov05_four_mode_snapshot_audit import run

SHA = "a" * 40
BLOB = "b" * 40
CODE = "202611050101"


def item(folder, code):
    return ("100644 blob " + BLOB + "\t" + folder + "/" + code + ".json\0").encode()


class November5MainSnapshotTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        archive_dir = self.root / "four_mode_forecasts"
        archive_dir.mkdir()
        self.archive = archive_dir / (CODE + ".json")
        self.archive.write_text(json.dumps({
            "race_code": CODE, "schema": "CLEAN_FOUR_MODES_PREDEADLINE_V1",
            "deadline_jst": "2026-11-05T15:20:00+09:00",
            "generated_at_jst": "2026-11-05T11:15:00+09:00",
            "source_title_received_jst": "2026-11-05T11:14:00+09:00",
            "source_cards_received_jst": "2026-11-05T11:14:30+09:00"
        }), encoding="utf-8")
        self.paths = item("four_mode_forecasts", CODE)
        self.score_calls = []

    def git(self, args):
        if args[:2] == ["rev-parse", "--verify"]:
            return (SHA + "\n").encode()
        if args[:3] == ["ls-tree", "-r", "-z"]:
            return self.paths
        raise AssertionError(args)

    def comparator(self, code, root):
        self.score_calls.append(code)
        return {"race_code": code, "status": "historical_comparison_only",
                "formal": False, "remote_first_seen_verified": False}

    def summarizer(self, codes, root, include_per_race):
        self.assertTrue(include_per_race)
        self.assertEqual(codes, [CODE])
        modes = {m: {k: int(m == "hit") for k in ("top1","top3","top5","top10")}
                 for m in ("narrow","hit","balance","hole")}
        per_race = {"race_code": CODE, "modes": {
            m: {"coverage_diagnostic": "covered" if m=="hit" else "winner_head_absent"}
            for m in modes}}
        return {"historical_comparable": 1, "topn_hits": modes,
                "pairwise_topn": {"hit_vs_hole": {"evaluated": 1}},
                "per_race": [per_race]}

    def test_same_race_and_real_result_content_only(self):
        self.paths += item("prospective_predictions", CODE)
        self.paths += item("confirmed_results", CODE)
        report = run(self.root, git=self.git, comparator=self.comparator,
                     summarizer=self.summarizer)
        self.assertEqual(report["four_mode_original_files"], 1)
        self.assertEqual(report["clean_separate_original_files"], 1)
        self.assertEqual(report["independent_result_filenames"], 1)
        self.assertEqual(report["four_mode_result_filename_intersection"], 1)
        self.assertEqual(report["result_content_comparable_count"], 1)
        self.assertEqual(report["historical_topn_hits"]["hit"]["top1"], 1)
        self.assertEqual(report["historical_topn_pct"]["hit"]["top10"], 100.0)
        self.assertEqual(report["historical_coverage_miss_reasons"]["hole"]
                         ["winner_head_absent"], 1)
        self.assertEqual(report["local_source_t12_diagnostic_only"]
                         ["local_claimed_T_minus_12_consistent"], 1)
        self.assertEqual(self.score_calls, [CODE])
        for field in ("formal", "prospective_accuracy_verified",
                      "github_remote_receipt_verified",
                      "first_git_add_chronology_verified",
                      "model_improvement_proven"):
            self.assertIs(report[field], False)

    def test_forecast_without_result_is_pending_not_miss(self):
        report = run(self.root, git=self.git, comparator=self.comparator,
                     summarizer=self.summarizer)
        self.assertEqual(report["four_mode_original_files"], 1)
        self.assertEqual(report["four_mode_result_filename_intersection"], 0)
        self.assertEqual(report["forecasts_without_result_filename"], [CODE])
        self.assertEqual(report["result_content_comparable_count"], 0)
        self.assertIsNone(report["historical_topn_hits"])
        self.assertIsNone(report["historical_topn_pct"])
        self.assertEqual(self.score_calls, [])

    def test_invalid_paired_result_withholds_all_rates(self):
        self.paths += item("confirmed_results", CODE)
        def bad(code, root):
            return {"race_code": code, "status": "invalid_result_or_timing",
                    "formal": False}
        report = run(self.root, git=self.git, comparator=bad,
                     summarizer=self.summarizer)
        self.assertEqual(report["four_mode_result_filename_intersection"], 1)
        self.assertEqual(report["result_content_comparable_count"], 0)
        self.assertEqual(len(report["untrusted_or_invalid_result_rows"]), 1)
        self.assertIsNone(report["historical_topn_pct"])
        self.assertIsNone(report["historical_pairwise_topn"])

    def test_old_and_invalid_race_codes_not_included(self):
        self.paths += item("four_mode_forecasts", "202611040101")
        self.paths += item("four_mode_forecasts", "202611052501")
        report = run(self.root, git=self.git)
        self.assertEqual(report["four_mode_original_files"], 1)

    def test_late_local_generation_does_not_get_false_t12_proof(self):
        raw = json.loads(self.archive.read_text())
        raw["generated_at_jst"] = "2026-11-05T15:10:00+09:00"
        self.archive.write_text(json.dumps(raw))
        report = run(self.root, git=self.git)
        self.assertEqual(report["local_source_t12_diagnostic_only"]
                         ["local_claimed_T_minus_12_inconsistent"], 1)
        self.assertFalse(report["first_git_add_chronology_verified"])

    def test_duplicate_main_tree_entry_rejected(self):
        self.paths += self.paths
        with self.assertRaisesRegex(ValueError, "unsafe_or_duplicate_git_tree_entry"):
            run(self.root, git=self.git)

    def test_corrupt_head_rejected(self):
        def git(args):
            return b"bad\n"
        with self.assertRaisesRegex(ValueError, "unverified_main_checkout_sha"):
            run(self.root, git=git)


if __name__ == "__main__":
    unittest.main()
