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
        self.assertEqual(evidence["ineligible_count"], 0)
        self.assertEqual(evidence["validation_error_count"], 0)
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

    def test_cutoff_crossed_during_prediction_is_ineligible(self):
        self.publish()
        after = datetime(2026, 11, 4, 2, 48, 1, tzinfo=timezone.utc)
        out = freeze_published(self.root, self.publication, NOW, self.git,
                               clock=lambda: after)
        self.assertEqual(out["frozen_before_t_minus_12"], 0)
        self.assertEqual(out["ineligible_count"], 1)
        self.assertEqual(out["records"][0]["reason"],
                         "calculation_crossed_t_minus_12")

    def test_freeze_end_time_is_used_not_only_start_time(self):
        self.publish()
        end = datetime(2026, 11, 4, 2, 47, 59, tzinfo=timezone.utc)
        out = freeze_published(self.root, self.publication, NOW, self.git,
                               clock=lambda: end)
        self.assertEqual(out["frozen_before_t_minus_12"], 1)
        self.assertEqual(out["records"][0]["frozen_at_utc"], end.isoformat())

    def test_capture_workflow_runs_third_freeze_before_hole_independently(self):
        workflow = (Path(__file__).resolve().parent /
                    ".github/workflows/four-mode-prospective-capture.yml").read_text()
        third = workflow.index("      - name: Freeze third-place research shadow")
        hole = workflow.index("      - name: Freeze shadow after confirmed publication")
        self.assertLess(third, hole)
        self.assertIn("if: ${{ always() && github.event_name != 'pull_request' }}",
                      workflow[third:hole])
        self.assertIn("four-mode-evidence/third-rate-shadow.json", workflow)

    def test_one_bad_race_does_not_erase_good_race_freeze(self):
        self.publish(added_forecasts=2)
        second = "202611040102"
        second_name = f"four_mode_forecasts/{second}.json"
        second_path = self.file.parent / f"{second}.json"
        record = json.loads(self.file.read_text())
        record["race_code"] = second
        second_path.write_text(json.dumps(record) + "\n", encoding="utf-8")
        def git(args):
            if args[0] == "rev-parse":
                return SHA + "\n"
            if args[0] == "diff-tree":
                return NAME + "\n" + second_name + "\n"
            if args[0] == "show":
                return "{}\n" if second_name in args[1] else self.file.read_text()
            raise AssertionError(args)
        report = freeze_published(self.root, self.publication, NOW, git)
        self.assertEqual(report["published_forecasts"], 2)
        self.assertEqual(report["frozen_before_t_minus_12"], 1)
        self.assertEqual(report["validation_error_count"], 1)
        self.assertEqual(report["ineligible_count"], 0)
        self.assertEqual(report["frozen_before_t_minus_12"] + report["ineligible_count"] +
                         report["validation_error_count"], report["published_forecasts"])
        self.assertEqual([row["status"] for row in report["records"]],
                         ["frozen_in_same_job_before_t_minus_12", "validation_error"])
        self.assertEqual([row["race_code"] for row in report["records"]], [CODE, second])
        self.assertFalse(report["independent_remote_first_seen_verified"])

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
        report = freeze_published(self.root, self.publication, NOW,
                                  lambda args: "{}\n" if args[0] == "show"
                                  else self.git(args))
        self.assertEqual(report["validation_error_count"], 1)
        self.assertEqual(report["frozen_before_t_minus_12"], 0)
        self.assertEqual(report["records"][0]["status"], "validation_error")

    def test_reject_changed_prediction_without_valid_reproduction(self):
        self.publish()
        record = json.loads(self.file.read_text())
        record["modes"]["hit"]["tickets"][0]["p"] += 0.01
        self.file.write_text(json.dumps(record) + "\n")
        report = freeze_published(self.root, self.publication, NOW, self.git)
        self.assertEqual(report["validation_error_count"], 1)
        self.assertEqual(report["frozen_before_t_minus_12"], 0)
        self.assertEqual(report["records"][0]["status"], "validation_error")


if __name__ == "__main__":
    unittest.main()
