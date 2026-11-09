"""Synthetic Git-only, result-blind source-to-candidate delivery accounting."""
from datetime import datetime
import json
import unittest

from four_mode_position_sensitive_forward import freeze_candidate
from position_sensitive_candidate_delivery_gap import audit_delivery_gap
from test_four_mode_position_sensitive_forward import archive

MAIN_SHA = "a"*40
LEDGER_SHA = "b"*40
ASOF = datetime.fromisoformat("2026-11-09T13:00:00+09:00")


def original(code, deadline):
    return json.dumps(archive(code=code, deadline=deadline), sort_keys=True).encode()


class FakeGit:
    def __init__(self):
        self.sources = {
            "202611090101": original("202611090101", "2026-11-09T12:40:00+09:00"),
            "202611090102": original("202611090102", "2026-11-09T12:40:00+09:00"),
            "202611090103": original("202611090103", "2026-11-09T15:40:00+09:00"),
        }
        one = self.sources["202611090101"]
        self.candidates = {
            "202611090101": json.dumps(
                freeze_candidate(one, "2026-11-09T10:05:00+09:00"),
                sort_keys=True).encode()
        }
        self.other_ledger = []
        self.calls = []

    def __call__(self, *argv):
        self.calls.append(argv)
        if "confirmed_results" in " ".join(argv) or "payout" in " ".join(argv):
            raise AssertionError("outcome_or_payout_leak")
        if argv[:2] == ("rev-parse", "--verify"):
            ref = argv[2]
            if ref == "refs/remotes/origin/main^{commit}":
                return (MAIN_SHA + "\n").encode()
            if ref == "refs/remotes/origin/position-sensitive-forward-evidence-ledger^{commit}":
                return (LEDGER_SHA + "\n").encode()
        if argv[:3] == ("ls-tree", "-r", "--name-only"):
            if argv[3] == MAIN_SHA:
                return ("\n".join(
                    ["four_mode_forecasts/"+code+".json" for code in sorted(self.sources)]
                    + ["four_mode_forecasts/202611080101.json",
                       "confirmed_results/202611090101.json"]) + "\n").encode()
            if argv[3] == LEDGER_SHA:
                return ("\n".join(
                    ["position_sensitive_research/README.md"] +
                    ["position_sensitive_research/"+code+".json" for code in self.candidates] +
                    self.other_ledger) + "\n").encode()
        if argv[0] == "show":
            ref = argv[1]
            if ref.startswith(MAIN_SHA + ":four_mode_forecasts/"):
                code = ref.split("/")[-1].removesuffix(".json")
                return self.sources[code]
            if ref.startswith(LEDGER_SHA + ":position_sensitive_research/"):
                code = ref.split("/")[-1].removesuffix(".json")
                return self.candidates[code]
        raise AssertionError("Unexpected Git access: " + repr(argv))


class CandidateDeliveryGapTests(unittest.TestCase):
    def test_real_race_style_one_saved_one_elapsed_one_still_open(self):
        git = FakeGit()
        report = audit_delivery_gap(git, "20261109", ASOF)
        self.assertEqual(report["eligible_original_exact_replays"], 3)
        self.assertEqual(report["candidate_files_on_day"], 1)
        self.assertEqual(report["candidate_exact_original_replays"], 1)
        self.assertEqual(report["originals_missing_candidate"], 2)
        self.assertEqual(len(report["per_race_complete_saved_original_roster"]), 3)
        self.assertEqual(len(report["pinned_snapshot_roster_sha256"]), 64)
        self.assertEqual(report["per_race_complete_saved_original_roster"][0]["candidate_saved"], True)
        self.assertEqual(len(report["per_race_complete_saved_original_roster"][0]["candidate_sha256"]), 64)
        self.assertEqual(
            len([r for r in report["per_race_complete_saved_original_roster"]
                 if r["candidate_sha256"] is None]), 2)
        repeated = audit_delivery_gap(git, "20261109", ASOF)
        self.assertEqual(report["pinned_snapshot_roster_sha256"],
                         repeated["pinned_snapshot_roster_sha256"])
        self.assertEqual(report["candidate_delivery_coverage_pct_of_eligible_original_files"], 33.33)
        self.assertEqual(report["status_counts"]["missing_candidate_local_window_still_open"], 1)
        self.assertEqual(report["status_counts"]["missing_candidate_local_window_elapsed"], 1)
        self.assertEqual(report["open_missing_race_examples"], ["202611090103"])
        self.assertEqual(report["elapsed_missing_race_examples"], ["202611090102"])
        self.assertEqual(report["candidate_first_remote_receipts_independently_verified"], 0)
        self.assertEqual(report["formal_forward_eligible_races"], 0)
        self.assertFalse(report["promotion_allowed"])
        self.assertFalse(report["model_improvement_proven"])

    def test_invalid_source_is_explicitly_excluded_not_candidate_missing(self):
        git = FakeGit()
        git.sources["202611090103"] = b"{invalid-json"
        x = audit_delivery_gap(git, "20261109", ASOF)
        self.assertEqual(x["eligible_original_exact_replays"], 2)
        self.assertEqual(x["originals_missing_candidate"], 1)
        self.assertEqual(len(x["invalid_original_files"]), 1)
        self.assertFalse(x["complete_capture_and_rescue_run_inventory_verified"])

    def test_invalid_candidate_source_is_hard_failure(self):
        git = FakeGit()
        git.sources["202611090101"] = b"{}"
        with self.assertRaises(ValueError):
            audit_delivery_gap(git, "20261109", ASOF)

    def test_candidate_without_original_in_main_is_hard_failure(self):
        git = FakeGit()
        git.candidates["202611090104"] = b"{}"
        with self.assertRaisesRegex(ValueError, "candidate_without_original"):
            audit_delivery_gap(git, "20261109", ASOF)

    def test_candidate_blob_mismatch_fails_entire_audit(self):
        git = FakeGit()
        data = json.loads(git.candidates["202611090101"])
        data["candidate"]["hit"][0] = "6-5-4"
        git.candidates["202611090101"] = json.dumps(data).encode()
        with self.assertRaisesRegex(ValueError, "saved_candidate_not_reproducible"):
            audit_delivery_gap(git, "20261109", ASOF)

    def test_unapproved_research_path_rejected(self):
        git = FakeGit()
        git.other_ledger = ["position_sensitive_research/extract-results.json"]
        with self.assertRaisesRegex(ValueError, "unapproved_research_candidate_path"):
            audit_delivery_gap(git, "20261109", ASOF)

    def test_excluded_Nov08_and_bad_dates_never_read_git(self):
        for day in ("20261108", "20270101", "2026-11-09", "../result"):
            git = FakeGit()
            with self.subTest(day=day), self.assertRaises(ValueError):
                audit_delivery_gap(git, day, ASOF)
            self.assertEqual(git.calls, [])

    def test_empty_saved_source_day_does_not_become_zero_denominator_success(self):
        git = FakeGit()
        git.sources.clear()
        git.candidates.clear()
        x = audit_delivery_gap(git, "20261109", ASOF)
        self.assertEqual(x["eligible_original_exact_replays"], 0)
        self.assertIsNone(x["candidate_delivery_coverage_pct_of_eligible_original_files"])
        self.assertEqual(x["formal_forward_eligible_races"], 0)

    def test_no_future_original_recorded_before_clock_provides_open_slot(self):
        git = FakeGit()
        future = json.loads(git.sources["202611090103"])
        future["generated_at_jst"] = "2026-11-09T14:00:00+09:00"
        future["source_title_received_jst"] = "2026-11-09T13:59:00+09:00"
        future["source_cards_received_jst"] = "2026-11-09T13:59:00+09:00"
        git.sources["202611090103"] = json.dumps(future).encode()
        x = audit_delivery_gap(git, "20261109", ASOF)
        self.assertEqual(
            x["status_counts"]["original_recorded_generation_after_observation_clock"], 1)
        self.assertEqual(x["status_counts"]["missing_candidate_local_window_still_open"], 0)


if __name__ == "__main__":
    unittest.main()
