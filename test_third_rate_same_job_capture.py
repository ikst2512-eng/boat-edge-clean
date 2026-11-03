import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from clean_four_modes import rank_modes
from research_model import probabilities
from third_rate_same_job_capture import freeze_published

SHA = "a" * 40
CODE = "202611040101"
NAME = f"four_mode_forecasts/{CODE}.json"
NOW = datetime(2026, 11, 4, 1, 0, tzinfo=timezone.utc)  # 10:00 JST
RATES = [4.2, 6.1, 5.7, 4.3, 5.2, 3.8]


class CaptureThirdRateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        folder = self.root / "four_mode_forecasts"
        folder.mkdir()
        record = {
            "schema": "CLEAN_FOUR_MODES_PREDEADLINE_V1",
            "race_code": CODE,
            "model_version": "CLEAN_FOUR_MODES_V2_PROVISIONAL_UNCALIBRATED",
            "generated_at_jst": "2026-11-04T09:30:00+09:00",
            "deadline_jst": "2026-11-04T12:00:00+09:00",
            "input_national_win_rates": RATES,
            "modes": rank_modes(probabilities(RATES)),
        }
        self.file = folder / f"{CODE}.json"
        self.file.write_text(json.dumps(record) + "\n", encoding="utf-8")
        self.publication = self.root / "publication.json"

    def publish(self, **changes):
        value = {"outcome": "pushed_to_main", "commit_sha": SHA,
                 "added_forecasts": 1}
        value.update(changes)
        self.publication.write_text(json.dumps(value), encoding="utf-8")

    def git(self, args):
        if args[0] == "rev-parse":
            return SHA + "\n"
        if args[0] == "diff-tree":
            return NAME + "\n"
        if args[0] == "show":
            return self.file.read_text(encoding="utf-8")
        raise AssertionError(args)

    def test_same_job_freezes_exact_tickets_without_any_results(self):
        self.publish()
        evidence = freeze_published(self.root, self.publication, NOW, self.git)
        self.assertEqual(evidence["published_forecasts"], 1)
        self.assertEqual(evidence["frozen_before_t_minus_12"], 1)
        item = evidence["records"][0]
        self.assertEqual(item["race_code"], CODE)
        self.assertEqual(item["status"], "frozen_in_same_job_before_t_minus_12")
        self.assertEqual(len(item["baseline_top10"]), 10)
        self.assertEqual(len(item["candidate_top10"]), 10)
        self.assertEqual(item["source_commit_sha"], SHA)
        self.assertEqual(item["t_minus_12_jst"], "2026-11-04T11:48:00+09:00")
        self.assertFalse(evidence["independent_remote_first_seen_verified"])
        self.assertFalse(evidence["production_forecast_changed"])

    def test_no_confirmed_publication_does_not_freeze(self):
        self.assertEqual(
            freeze_published(self.root, self.publication)["frozen_before_t_minus_12"], 0)
        self.publish(outcome="no_eligible_candidates")
        self.assertEqual(freeze_published(
            self.root, self.publication)["status"], "no_confirmed_publication")

    def test_past_cutoff_never_freezes_candidate(self):
        self.publish()
        at_cutoff = datetime(2026, 11, 4, 2, 48, tzinfo=timezone.utc)
        out = freeze_published(self.root, self.publication, at_cutoff, self.git)
        self.assertEqual(out["frozen_before_t_minus_12"], 0)
        self.assertEqual(out["records"][0]["reason"], "after_t_minus_12")

    def test_invalid_commit_count_and_head_fail_closed(self):
        self.publish(added_forecasts=2)
        with self.assertRaises(ValueError):
            freeze_published(self.root, self.publication, NOW, self.git)
        self.publish()
        with self.assertRaisesRegex(ValueError, "publication_commit_not_checkout_head"):
            freeze_published(self.root, self.publication, NOW,
                             lambda args: "b" * 40 if args[0] == "rev-parse"
                             else self.git(args))

    def test_git_original_blob_must_match_archive_bytes(self):
        self.publish()
        with self.assertRaisesRegex(ValueError, "first_add_blob_changed"):
            freeze_published(self.root, self.publication, NOW,
                             lambda args: "{}\n" if args[0] == "show"
                             else self.git(args))

    def test_reject_changed_prediction_without_valid_reproduction(self):
        self.publish()
        record = json.loads(self.file.read_text())
        record["modes"]["hit"]["tickets"][0]["p"] += 0.01
        self.file.write_text(json.dumps(record) + "\n")
        with self.assertRaisesRegex(ValueError, "saved_forecast_not_reproducible"):
            freeze_published(self.root, self.publication, NOW, self.git)


if __name__ == "__main__":
    unittest.main()
