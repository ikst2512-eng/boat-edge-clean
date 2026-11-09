"""Synthetic, result-blind tests for later-main race-ID missingness audit."""
import copy
import subprocess
import unittest

from research import hole_pair_snapshot_id_drift_audit as m

DAY = "20261109"
A = DAY + "0101"
B = DAY + "0102"
C = DAY + "0103"
D = DAY + "0104"
INITIAL_SHA = "a" * 40
LATER_SHA = "b" * 40


def batch():
    return {
        "schema": "HOLE_PAIR_FUTURE_ACTIONS_BATCH_V1",
        "status": "local_predeadline_freeze_not_formal",
        "capture_day_jst": DAY,
        "source_main_commit": INITIAL_SHA,
        "source_forecast_codes": [A, B],
        "records": [{"race_code": A}],
        "excluded_race_codes_by_reason": {"after_t_minus_12": [B]},
        "excluded_by_reason": {"after_t_minus_12": 1},
        "eligible_forecasts_examined": 2,
        "frozen_count": 1,
        "source_snapshot_coverage": {
            "source_main_commit": INITIAL_SHA,
            "capture_day_jst": DAY,
            "snapshot_forecasts_examined": 2,
            "frozen_locally_unverified": 1,
            "source_snapshot_race_coverage_complete": True,
            "entire_day_or_official_schedule_complete_verified": False,
            "excluded_by_reason": {"after_t_minus_12": 1},
            "excluded_race_codes_by_reason": {"after_t_minus_12": [B]},
            "frozen_codes_by_candidate_cutoff_order": [A],
        },
        "formal": False,
        "prospective_validation": False,
        "independent_first_receipt_verified": False,
        "production_forecast_changed": False,
    }


class SnapshotDriftTests(unittest.TestCase):
    def compare(self, ids=None, original=None, sha=LATER_SHA, verified=True):
        return m.audit(batch() if original is None else original,
                       sha, [A, B] if ids is None else ids,
                       descendant_verified=verified)

    def test_no_new_ids_does_not_prove_whole_day_or_formal(self):
        x = self.compare()
        self.assertEqual(x["newly_visible_count"], 0)
        self.assertEqual(x["missing_original_count"], 0)
        self.assertFalse(x["formal"])
        self.assertFalse(x["whole_day_or_official_schedule_complete_verified"])
        self.assertFalse(x["source_content_or_blob_identity_rechecked"])
        self.assertEqual(x["pilot_formally_eligible"], 0)
        self.assertEqual(x["confirmation_formally_eligible"], 0)
        self.assertIn("still_unverified", x["status"])

    def test_later_day_forecast_appears_without_retroactive_freeze(self):
        x = self.compare([A, B, C])
        self.assertEqual(x["newly_visible_race_codes"], [C])
        self.assertEqual(x["newly_visible_count"], 1)
        self.assertEqual(x["initial_ids_missing_in_later_snapshot"], [])
        self.assertEqual(x["status"], "id_drift_observed_requires_missingness_review")
        self.assertEqual(x["pilot_formally_eligible"], 0)

    def test_later_source_loss_and_change_both_are_listed(self):
        self.assertEqual(self.compare([A])["initial_ids_missing_in_later_snapshot"], [B])
        x = self.compare([A, C, D])
        self.assertEqual(x["newly_visible_race_codes"], [C, D])
        self.assertEqual(x["initial_ids_missing_in_later_snapshot"], [B])

    def test_identical_commit_cannot_claim_changed_immutable_roster(self):
        with self.assertRaisesRegex(ValueError, "same_immutable_commit"):
            self.compare([A, B, C], sha=INITIAL_SHA)
        self.assertEqual(self.compare(sha=INITIAL_SHA)["newly_visible_count"], 0)

    def test_unverified_ancestry_rejected_even_when_ids_match(self):
        with self.assertRaisesRegex(ValueError, "untrusted_main_history"):
            self.compare(verified=False)

    def test_outcome_based_formal_or_fake_snapshot_flags_rejected(self):
        for mutate in (
            lambda x: x.update(formal=True),
            lambda x: x.update(independent_first_receipt_verified=True),
            lambda x: x["source_snapshot_coverage"].update(
                entire_day_or_official_schedule_complete_verified=True),
            lambda x: x.update(frozen_count=0),
            lambda x: x.update(eligible_forecasts_examined=3),
        ):
            x = batch()
            mutate(x)
            with self.subTest(x=x), self.assertRaises(ValueError):
                self.compare(original=x)

    def test_malformed_duplicated_unsorted_or_foreign_race_ids_rejected(self):
        for ids in (
            [B, A], [A, A], [A, B, "202611100101"],
            [A, B, DAY + "2501"], [A, B, DAY + "0113"],
            [A, B, "202611099999"], [A, B, "202611090101.json"],
        ):
            with self.subTest(ids=ids), self.assertRaises(ValueError):
                self.compare(ids)

    def test_missing_or_duplicated_original_classification_rejected(self):
        for mutate in (
            lambda x: x["records"].clear(),
            lambda x: x["excluded_race_codes_by_reason"].update(after_t_minus_12=[A]),
            lambda x: x["source_forecast_codes"].append(B),
            lambda x: x["source_snapshot_coverage"].update(
                frozen_codes_by_candidate_cutoff_order=[B]),
        ):
            x = batch()
            mutate(x)
            with self.subTest(x=x), self.assertRaises(ValueError):
                self.compare(original=x)

    def test_git_audit_checks_ancestry_then_readonly_forecast_tree(self):
        calls = []
        def fake_run(argv, **kwargs):
            calls.append(argv)
            if argv[1] == "merge-base":
                return subprocess.CompletedProcess(argv, 0, "", "")
            assert argv[1] == "ls-tree"
            return subprocess.CompletedProcess(argv, 0, "\n".join([
                "four_mode_forecasts/" + A + ".json",
                "four_mode_forecasts/" + B + ".json",
                "four_mode_forecasts/" + C + ".json",
                "four_mode_forecasts/202611080101.json",
                "confirmed_results/202611090101.json",
            ]) + "\n", "")
        x = m.audit_git(batch(), LATER_SHA, run=fake_run)
        self.assertEqual(x["newly_visible_race_codes"], [C])
        self.assertEqual(calls[0][:3], ["git", "merge-base", "--is-ancestor"])
        self.assertEqual(calls[1][:4], ["git", "ls-tree", "-r", "--name-only"])
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[1][-1], "four_mode_forecasts/")

    def test_non_descendant_refused_before_source_tree_read(self):
        calls = []
        def fake_run(argv, **kwargs):
            calls.append(argv)
            return subprocess.CompletedProcess(argv, 1, "", "")
        with self.assertRaisesRegex(ValueError, "not_verified_descendant"):
            m.audit_git(batch(), LATER_SHA, run=fake_run)
        self.assertEqual(len(calls), 1)

    def test_later_git_tree_failure_or_suspicious_same_day_path(self):
        for status, listing in (
            (1, ""),
            (0, "four_mode_forecasts/" + DAY + "bad.json\n"),
        ):
            def fake_run(argv, **kwargs):
                if argv[1] == "merge-base":
                    return subprocess.CompletedProcess(argv, 0, "", "")
                return subprocess.CompletedProcess(argv, status, listing, "")
            with self.assertRaises(ValueError):
                m.audit_git(batch(), LATER_SHA, run=fake_run)

    def test_bad_commit_sha_rejected_before_any_git_call(self):
        def forbidden(*args, **kwargs):
            self.fail("git must not run")
        with self.assertRaisesRegex(ValueError, "invalid_git_commit_identity"):
            m.audit_git(batch(), "main", run=forbidden)


if __name__ == "__main__":
    unittest.main()
