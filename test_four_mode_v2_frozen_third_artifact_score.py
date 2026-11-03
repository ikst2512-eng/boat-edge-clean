import hashlib
import io
import json
import tempfile
import unittest
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from clean_four_modes import rank_modes
from research_model import probabilities
from four_mode_v2_third_rate_shadow import PROTOCOL, candidate
from four_mode_v2_frozen_third_artifact_score import score_evidence, score_zip

CODE = "202611040101"
SHA = "a" * 40
RATES = [5.2, 6.1, 4.6, 3.9, 4.8, 3.7]


class FrozenArtifactScoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        folder = self.root / "four_mode_forecasts"
        folder.mkdir()
        modes = rank_modes(probabilities(RATES))
        archive = {"race_code": CODE, "model_version":
                   "CLEAN_FOUR_MODES_V2_PROVISIONAL_UNCALIBRATED",
                   "modes": modes}
        self.path = folder / (CODE + ".json")
        self.path.write_text(json.dumps(archive) + "\n", encoding="utf-8")
        baseline = [x["combo"] for x in modes["hit"]["tickets"]]
        picks, _ = candidate(baseline, RATES, probabilities(RATES))
        self.evidence = {
            "schema": "V2_THIRD_RATE_SAME_JOB_FROZEN_SHADOW_V1",
            "protocol": PROTOCOL, "formal": False,
            "independent_remote_first_seen_verified": False,
            "production_forecast_changed": False,
            "status": "captured_local_after_push_not_remote_proven",
            "publication_commit_sha": SHA, "published_forecasts": 1,
            "frozen_before_t_minus_12": 1, "ineligible_count": 0,
            "records": [{
                "race_code": CODE, "status": "frozen_in_same_job_before_t_minus_12",
                "source_commit_sha": SHA, "protocol": PROTOCOL,
                "baseline_top10": baseline, "candidate_top10": picks,
                "frozen_at_utc": "2026-11-04T01:00:00+00:00",
                "t_minus_12_jst": "2026-11-04T11:48:00+09:00",
                "source_forecast_sha256": hashlib.sha256(self.path.read_bytes()).hexdigest(),
            }],
        }

    def test_frozen_candidate_is_scored_exactly_not_recomputed(self):
        ticket = self.evidence["records"][0]["candidate_top10"][0]
        with patch("four_mode_v2_frozen_third_artifact_score.compare_race",
                   return_value={"status": "historical_comparison_only",
                                 "winning_ticket": ticket}):
            report = score_evidence(self.evidence, self.root)
        self.assertEqual(report["paired"], 1)
        self.assertEqual(report["topn"]["top3"]["candidate"], 1)
        self.assertEqual(report["race_codes_paired"], [CODE])
        self.assertEqual(report["paired_race_scores"][0]["race_code"], CODE)
        self.assertEqual(report["paired_race_scores"][0]["topn"]["top3"]["candidate"], 1)
        self.assertFalse(report["formal"])
        self.assertFalse(report["production_promotion_allowed"])

    def test_missing_result_is_pending_not_loss(self):
        with patch("four_mode_v2_frozen_third_artifact_score.compare_race",
                   return_value={"status": "result_unavailable"}):
            report = score_evidence(self.evidence, self.root)
        self.assertEqual(report["paired"], 0)
        self.assertEqual(report["pending_results"], 1)
        self.assertEqual(report["topn"]["top10"]["baseline"], 0)

    def test_archive_sha_change_is_invalid_and_unscored(self):
        self.path.write_bytes(self.path.read_bytes() + b"x")
        with patch("four_mode_v2_frozen_third_artifact_score.compare_race") as compare:
            report = score_evidence(self.evidence, self.root)
        compare.assert_not_called()
        self.assertEqual(report["invalid"], 1)

    def test_after_cutoff_and_dev_day_are_never_scored(self):
        self.evidence["records"][0]["frozen_at_utc"] = "2026-11-04T02:48:00+00:00"
        with patch("four_mode_v2_frozen_third_artifact_score.compare_race") as compare:
            report = score_evidence(self.evidence, self.root)
        compare.assert_not_called()
        self.assertEqual(report["invalid"], 1)

    def test_tampered_ticket_ranking_is_rejected(self):
        self.evidence["records"][0]["baseline_top10"][0] = "6-5-4"
        with patch("four_mode_v2_frozen_third_artifact_score.compare_race") as compare:
            report = score_evidence(self.evidence, self.root)
        compare.assert_not_called()
        self.assertEqual(report["invalid"], 1)

    def test_one_validation_error_does_not_erase_valid_frozen_race(self):
        # Match the producer's real mutually-exclusive status partition:
        # one valid freeze and one validation_error, never two exclusions.
        second = "202611040102"
        self.evidence["published_forecasts"] = 2
        self.evidence["validation_error_count"] = 1
        self.evidence["records"].append({
            "race_code": second, "status": "validation_error",
            "error_type": "ValueError"})
        with patch("four_mode_v2_frozen_third_artifact_score.compare_race",
                   return_value={"status": "result_unavailable"}):
            result = score_evidence(self.evidence, self.root)
        self.assertEqual(result["frozen"], 1)
        self.assertEqual(result["pending_results"], 1)
        self.assertEqual(result["invalid"], 1)
        self.assertEqual(result["excluded"], 0)
        self.assertEqual(result["race_codes_frozen"], [CODE])
        self.assertEqual(result["validation_error_count"], 1)

    def test_validation_error_count_must_equal_exact_records(self):
        self.evidence["validation_error_count"] = 1
        with self.assertRaisesRegex(ValueError,
                                    "artifact_validation_error_count_inconsistent"):
            score_evidence(self.evidence, self.root)

    def test_ineligible_record_is_not_a_validation_error(self):
        self.evidence["records"][0] = {
            "race_code": CODE, "status": "ineligible", "reason": "after_t_minus_12"}
        self.evidence["frozen_before_t_minus_12"] = 0
        self.evidence["ineligible_count"] = 1
        result = score_evidence(self.evidence, self.root)
        self.assertEqual(result["excluded"], 1)
        self.assertEqual(result["invalid"], 0)
        self.assertEqual(result["frozen"], 0)

    def test_no_publication_yields_zero_denominator(self):
        self.evidence.update({"status": "no_confirmed_publication",
                              "published_forecasts": 0,
                              "frozen_before_t_minus_12": 0,
                              "records": []})
        report = score_evidence(self.evidence, self.root)
        self.assertEqual(report["paired"], 0)
        self.assertEqual(report["published_forecasts"], 0)

    def test_reject_duplicate_record_or_wrong_count(self):
        self.evidence["records"].append(dict(self.evidence["records"][0]))
        self.evidence["published_forecasts"] = 2
        self.evidence["frozen_before_t_minus_12"] = 2
        with self.assertRaisesRegex(ValueError, "invalid_or_duplicate_race"):
            score_evidence(self.evidence, self.root)
        self.evidence["records"] = [self.evidence["records"][0]]
        with self.assertRaisesRegex(ValueError, "artifact_publication_roster_inconsistent"):
            score_evidence(self.evidence, self.root)

    def test_zip_file_directly_consumes_original_artifact(self):
        path = self.root / "artifact.zip"
        with zipfile.ZipFile(path, "w") as z:
            z.writestr("four-mode-evidence/third-rate-shadow.json",
                       json.dumps(self.evidence))
        with patch("four_mode_v2_frozen_third_artifact_score.compare_race",
                   return_value={"status": "result_unavailable"}):
            result = score_zip(path, self.root)
        self.assertEqual(result["pending_results"], 1)
        with zipfile.ZipFile(path, "a") as z:
            z.writestr("third-rate-shadow.json", json.dumps(self.evidence))
        with self.assertRaisesRegex(ValueError, "missing_duplicate"):
            score_zip(path, self.root)


if __name__ == "__main__":
    unittest.main()
