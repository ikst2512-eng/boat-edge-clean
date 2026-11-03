import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from clean_four_modes import rank_modes
from research_model import probabilities
from four_mode_v2_third_rate_shadow import PROTOCOL, candidate
from four_mode_v2_frozen_third_nightly import choose_runs, summarize

CODE = "202611040101"
SHA = "a" * 40
RATES = [5.2, 6.1, 4.6, 3.9, 4.8, 3.7]


def run(id, at="2026-11-04T01:00:00Z", event="schedule", branch="main",
        conclusion="success"):
    return {"databaseId": id, "createdAt": at, "event": event,
            "headBranch": branch, "conclusion": conclusion}


class FrozenNightlyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        folder = self.root / "four_mode_forecasts"
        folder.mkdir()
        modes = rank_modes(probabilities(RATES))
        archived = {"race_code": CODE,
                    "model_version": "CLEAN_FOUR_MODES_V2_PROVISIONAL_UNCALIBRATED",
                    "modes": modes}
        file = folder / (CODE + ".json")
        file.write_text(json.dumps(archived) + "\n")
        baseline = [row["combo"] for row in modes["hit"]["tickets"]]
        picks, _ = candidate(baseline, RATES, probabilities(RATES))
        self.evidence = {
            "schema": "V2_THIRD_RATE_SAME_JOB_FROZEN_SHADOW_V1",
            "protocol": PROTOCOL,
            "formal": False,
            "independent_remote_first_seen_verified": False,
            "production_forecast_changed": False,
            "status": "captured_local_after_push_not_remote_proven",
            "publication_commit_sha": SHA,
            "published_forecasts": 1,
            "frozen_before_t_minus_12": 1,
            "ineligible_count": 0,
            "records": [{
                "race_code": CODE, "status": "frozen_in_same_job_before_t_minus_12",
                "source_commit_sha": SHA, "protocol": PROTOCOL,
                "baseline_top10": baseline, "candidate_top10": picks,
                "frozen_at_utc": "2026-11-04T01:00:00+00:00",
                "t_minus_12_jst": "2026-11-04T11:48:00+09:00",
                "source_forecast_sha256": hashlib.sha256(file.read_bytes()).hexdigest(),
            }],
        }

    def download(self, id, path):
        with zipfile.ZipFile(path, "w") as z:
            z.writestr("four-mode-evidence/third-rate-shadow.json",
                       json.dumps(self.evidence))

    def test_no_future_runs_is_zero_not_accuracy(self):
        out = summarize([run(1, "2026-11-03T11:00:00Z")],
                        self.root, self.download, self.root)
        self.assertEqual(out["status"], "no_future_capture_runs")
        self.assertEqual(out["paired"], 0)
        self.assertFalse(out["production_promotion_allowed"])

    def test_only_main_future_capture_not_pr(self):
        inventory = [
            run(10, "2026-11-03T14:59:59Z"),
            run(11, event="pull_request"),
            run(12, branch="dev"),
            run(13, conclusion=""),
            run(14, "2026-11-04T01:00:00Z", "workflow_dispatch"),
        ]
        self.assertEqual([x[1] for x in choose_runs(inventory)], [14])

    def test_frozen_actual_artifact_scored_without_recalculation(self):
        finish = self.evidence["records"][0]["candidate_top10"][0]
        with patch("four_mode_v2_frozen_third_artifact_score.compare_race",
                   return_value={"status": "historical_comparison_only",
                                 "winning_ticket": finish}):
            out = summarize([run(123)], self.root, self.download, self.root)
        self.assertEqual(out["status"], "scored_frozen_artifacts")
        self.assertEqual(out["paired"], 1)
        self.assertEqual(out["topn"]["top3"]["candidate"], 1)
        self.assertEqual(out["race_codes_paired"], [CODE])
        self.assertFalse(out["remote_first_seen_independently_verified"])

    def test_duplicate_race_across_two_artifacts_fails_closed(self):
        with patch("four_mode_v2_frozen_third_artifact_score.compare_race",
                   return_value={"status": "result_unavailable"}):
            with self.assertRaisesRegex(ValueError, "duplicate_frozen_race"):
                summarize([run(123), run(124)], self.root,
                          self.download, self.root)

    def test_missing_artifact_is_explicit_incomplete_not_zero_hit(self):
        def fail(id, path):
            raise OSError("artifact unavailable")
        out = summarize([run(123)], self.root, fail, self.root)
        self.assertEqual(out["status"], "capture_artifacts_unavailable")
        self.assertEqual(out["missing_or_failed_artifacts"], [123])
        self.assertEqual(out["paired"], 0)

    def test_reject_duplicate_run_ids(self):
        with self.assertRaisesRegex(ValueError, "duplicate_run_id"):
            choose_runs([run(123), run(123)])


if __name__ == "__main__":
    unittest.main()
