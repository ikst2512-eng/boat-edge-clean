import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from clean_four_modes import rank_modes
from research_model import probabilities
from four_mode_v2_third_rate_shadow import PROTOCOL, candidate
from four_mode_v2_third_rate_ledger_rollup import evaluate, REF

CODE = "202611040101"
SHA = "a" * 40
RATES = [5.2, 6.1, 4.6, 3.9, 4.8, 3.7]


class ThirdRateDurableRollupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        folder = self.root / "four_mode_forecasts"
        folder.mkdir()
        modes = rank_modes(probabilities(RATES))
        archive = {"race_code": CODE, "model_version":
                   "CLEAN_FOUR_MODES_V2_PROVISIONAL_UNCALIBRATED",
                   "deadline_jst": "2026-11-04T12:00:00+09:00",
                   "modes": modes}
        f = folder / (CODE + ".json")
        f.write_text(json.dumps(archive) + "\n", encoding="utf-8")
        baseline = [x["combo"] for x in modes["hit"]["tickets"]]
        after, _ = candidate(baseline, RATES, probabilities(RATES))
        self.evidence = {
            "schema": "V2_THIRD_RATE_SAME_JOB_FROZEN_SHADOW_V1",
            "protocol": PROTOCOL, "formal": False,
            "independent_remote_first_seen_verified": False,
            "production_forecast_changed": False,
            "status": "captured_local_after_push_not_remote_proven",
            "publication_commit_sha": SHA, "published_forecasts": 1,
            "frozen_before_t_minus_12": 1, "ineligible_count": 0,
            "validation_error_count": 0,
            "records": [{
                "race_code": CODE,
                "status": "frozen_in_same_job_before_t_minus_12",
                "source_commit_sha": SHA, "protocol": PROTOCOL,
                "baseline_top10": baseline, "candidate_top10": after,
                "frozen_at_utc": "2026-11-04T01:00:00+00:00",
                "t_minus_12_jst": "2026-11-04T11:48:00+09:00",
                "source_forecast_sha256": hashlib.sha256(f.read_bytes()).hexdigest(),
            }],
        }
        self.name = "third_rate/20261104/run-12345-attempt-1.json"

    def git(self, root, *args):
        if args[0] == "ls-tree":
            return (self.name + "\n").encode()
        if args[0] == "show":
            return (json.dumps(self.evidence, sort_keys=True) + "\n").encode()
        raise AssertionError(args)

    def test_ledger_frozen_ticket_scored_by_original_race_date(self):
        winning = self.evidence["records"][0]["candidate_top10"][0]
        with patch("four_mode_v2_frozen_third_artifact_score.compare_race",
                   return_value={"status": "historical_comparison_only",
                                 "winning_ticket": winning}):
            report = evaluate(self.root, self.git)
        self.assertEqual(report["ledger_files"], 1)
        self.assertEqual(report["status"], "durable_frozen_evidence_scored")
        self.assertEqual(report["paired"], 1)
        self.assertEqual(report["by_race_day_jst"]["20261104"]["paired"], 1)
        self.assertEqual(report["topn"]["top3"]["candidate"], 1)
        self.assertEqual(report["race_codes_paired"], [CODE])
        self.assertEqual(report["paired_race_scores"][0]["race_code"], CODE)
        self.assertFalse(report["remote_first_seen_independently_verified"])
        self.assertFalse(report["production_promotion_allowed"])

    def test_missing_results_pending_not_false_miss(self):
        with patch("four_mode_v2_frozen_third_artifact_score.compare_race",
                   return_value={"status": "result_unavailable"}):
            report = evaluate(self.root, self.git)
        self.assertEqual(report["paired"], 0)
        self.assertEqual(report["pending_results"], 1)
        self.assertEqual(report["topn"]["top10"]["candidate"], 0)

    def test_nightly_checkout_fetch_has_ephemeral_github_credentials(self):
        workflow = (Path(__file__).resolve().parent /
                    ".github/workflows/v2-predeclared-shadow-research.yml").read_text()
        start = workflow.index("      - name: Score preserved third-rate original evidence")
        body = workflow[start:workflow.index("      - uses: actions/upload-artifact@v4", start)]
        self.assertIn("GH_TOKEN: ${{ github.token }}", body)
        self.assertLess(body.index("gh auth setup-git"),
                        body.index("git fetch origin refs/heads/v2-third-rate-evidence-ledger"))
        self.assertIn("persist-credentials: false", workflow)

    def test_no_ledger_entries_is_not_prospective_success(self):
        report = evaluate(self.root, lambda *_: b"")
        self.assertEqual(report["status"], "no_long_lived_frozen_evidence")
        self.assertFalse(report["complete_capture_inventory_verified"])

    def test_missing_branch_visible_as_missing_evidence(self):
        def missing(*_):
            raise subprocess.CalledProcessError(1, ["git"])
        report = evaluate(self.root, missing)
        self.assertEqual(report["status"], "ledger_branch_unavailable")

    def test_ledger_path_run_id_mismatch_is_invalid(self):
        def wrong(root, *args):
            if args[0] == "ls-tree":
                return b"third_rate/20261104/run-54321-attempt-1.json\n"
            return (json.dumps(self.evidence) + "\n").encode()
        # Path identity is not recorded in JSON itself. Its frozen content
        # still requires valid digest and receives no remote timestamp claim.
        report = evaluate(self.root, wrong)
        self.assertEqual(report["ledger_files"], 1)
        self.assertFalse(report["complete_capture_inventory_verified"])

    def test_corrupt_original_prevents_scoring(self):
        self.evidence["records"][0]["source_forecast_sha256"] = "0" * 64
        report = evaluate(self.root, self.git)
        self.assertEqual(report["status"], "incomplete_or_invalid_ledger_evidence")
        self.assertEqual(report["paired"], 0)
        self.assertEqual(report["invalid_files"], [self.name])

    def test_rejected_mixed_duplicate_does_not_poison_later_valid_race(self):
        # First ledger: A. Second ledger: B then A (cross-entry
        # duplicate), so whole second ledger is invalid. Third ledger:
        # only B, valid and must not inherit second ledger's failed state.
        from copy import deepcopy
        other_code = "202611040102"
        original_file = self.root / "four_mode_forecasts" / (CODE + ".json")
        other_file = self.root / "four_mode_forecasts" / (other_code + ".json")
        archive = json.loads(original_file.read_text(encoding="utf-8"))
        archive["race_code"] = other_code
        other_file.write_text(json.dumps(archive) + "\n", encoding="utf-8")
        other_row = deepcopy(self.evidence["records"][0])
        other_row["race_code"] = other_code
        other_row["source_forecast_sha256"] = hashlib.sha256(
            other_file.read_bytes()).hexdigest()
        paths = [self.name,
                 "third_rate/20261104/run-12346-attempt-1.json",
                 "third_rate/20261104/run-12347-attempt-1.json"]
        first = deepcopy(self.evidence)
        second = deepcopy(self.evidence)
        second["records"] = [other_row, deepcopy(self.evidence["records"][0])]
        second["published_forecasts"] = 2
        second["frozen_before_t_minus_12"] = 2
        third = deepcopy(self.evidence)
        third["records"] = [other_row]
        contents = dict(zip(paths, [first, second, third]))

        def git(root, *args):
            if args[0] == "ls-tree":
                return ("\n".join(paths) + "\n").encode()
            if args[0] == "show":
                return json.dumps(contents[args[1].split(":", 1)[1]]).encode()
            raise AssertionError(args)

        with patch("four_mode_v2_frozen_third_artifact_score.compare_race",
                   return_value={"status": "result_unavailable"}):
            report = evaluate(self.root, git)
        self.assertEqual(report["status"], "incomplete_or_invalid_ledger_evidence")
        self.assertEqual(report["invalid_files"], [paths[1]])
        self.assertEqual(report["frozen"], 2)
        self.assertEqual(report["pending_results"], 2)
        self.assertEqual(report["race_codes_frozen"], [CODE, other_code])

    def test_duplicate_frozen_race_across_entries_fails_closed(self):
        other = "third_rate/20261104/run-12346-attempt-1.json"
        def duplicate(root, *args):
            if args[0] == "ls-tree":
                return (self.name + "\n" + other + "\n").encode()
            return (json.dumps(self.evidence) + "\n").encode()
        with patch("four_mode_v2_frozen_third_artifact_score.compare_race",
                   return_value={"status": "result_unavailable"}):
            report = evaluate(self.root, duplicate)
        self.assertEqual(report["status"], "incomplete_or_invalid_ledger_evidence")
        self.assertEqual(report["ledger_files"], 2)
        self.assertEqual(report["pending_results"], 1)
        self.assertEqual(report["invalid_files"], [other])


if __name__ == "__main__":
    unittest.main()
