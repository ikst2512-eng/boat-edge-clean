"""Synthetic source Git-tree drift tests; never open race results or refreeze."""
import copy
import subprocess
import unittest

from research import hole_pair_source_blob_drift_audit as d
from research.test_hole_pair_snapshot_id_drift_audit import (
    batch as base_batch, A, B, C, DAY, INITIAL_SHA, LATER_SHA,
)

BLOB_A = "1" * 40
BLOB_B = "2" * 40
BLOB_C = "3" * 40
BLOB_CHANGED = "4" * 40


def tree(mapping):
    return "".join(
        f"100644 blob {sha}\tfour_mode_forecasts/{code}.json\n"
        for code, sha in sorted(mapping.items())
    )


def batch():
    obj = base_batch()
    obj["records"][0]["source_git_blob_sha1"] = BLOB_A
    return obj


class SourceBlobDriftTests(unittest.TestCase):
    def check(self, prior=None, later=None, manifest=None, sha=LATER_SHA, descendant=True):
        return d.audit_trees(
            batch() if manifest is None else manifest,
            sha,
            tree({A: BLOB_A, B: BLOB_B}) if prior is None else prior,
            tree({A: BLOB_A, B: BLOB_B}) if later is None else later,
            descendant_verified=descendant,
        )

    def test_identical_tree_does_not_claim_formal_or_day_coverage(self):
        r = self.check()
        self.assertTrue(r["initial_source_tree_matches_manifest_ids"])
        self.assertTrue(r["initial_frozen_git_blob_claims_match_original_tree"])
        self.assertEqual(r["changed_same_race_source_git_blob_count"], 0)
        self.assertFalse(r["raw_source_content_sha256_independently_verified"])
        self.assertFalse(r["first_remote_receipt_verified"])
        self.assertFalse(r["whole_day_or_official_schedule_complete_verified"])
        self.assertFalse(r["formal"])
        self.assertEqual(r["pilot_formally_eligible"], 0)

    def test_same_race_id_blob_mutation_is_detected_and_quarantined(self):
        r = self.check(later=tree({A: BLOB_CHANGED, B: BLOB_B}))
        self.assertEqual(r["changed_same_race_source_git_blob_codes"], [A])
        self.assertEqual(r["changed_same_race_source_git_blob_count"], 1)
        self.assertEqual(r["changed_same_race_git_blob_pairs"][A],
                         {"original_git_blob_sha1": BLOB_A,
                          "later_git_blob_sha1": BLOB_CHANGED})
        self.assertEqual(r["status"], "same_race_source_blob_drift_quarantine_and_review")
        self.assertFalse(r["production_promotion_allowed"])

    def test_added_and_removed_ids_still_reported_without_new_candidate(self):
        r = self.check(later=tree({A: BLOB_A, C: BLOB_C}))
        self.assertEqual(r["newly_visible_race_codes"], [C])
        self.assertEqual(r["initial_ids_missing_in_later_snapshot"], [B])
        self.assertEqual(r["changed_same_race_source_git_blob_codes"], [])
        self.assertEqual(r["confirmation_formally_eligible"], 0)

    def test_frozen_claim_must_match_original_git_tree_not_later(self):
        obj = batch()
        obj["records"][0]["source_git_blob_sha1"] = BLOB_CHANGED
        with self.assertRaisesRegex(ValueError, "frozen_source_git_blob_claim_mismatch"):
            self.check(manifest=obj)

    def test_original_manifest_id_census_checked_against_actual_git_tree(self):
        with self.assertRaisesRegex(ValueError, "original_manifest_source_ids_differ"):
            self.check(prior=tree({A: BLOB_A, C: BLOB_C}))

    def test_untrusted_or_ambiguous_same_day_git_tree_rejected(self):
        bad = (
            f"120000 blob {BLOB_A}\tfour_mode_forecasts/{A}.json\n",
            f"160000 commit {BLOB_A}\tfour_mode_forecasts/{A}.json\n",
            f"100644 blob {'x'*40}\tfour_mode_forecasts/{A}.json\n",
            f"100644 blob {BLOB_A}\tfour_mode_forecasts/{A}.json\n"
            f"100644 blob {BLOB_CHANGED}\tfour_mode_forecasts/{A}.json\n",
            f"100644 blob {BLOB_A}\tfour_mode_forecasts/{DAY}bad.json\n",
            f"100644 blob {BLOB_A}\tfour_mode_forecasts/{DAY}2501.json\n",
        )
        for broken in bad:
            with self.subTest(broken=broken), self.assertRaises(ValueError):
                self.check(prior=broken)

    def test_changed_earlier_day_does_not_enter_same_day_census(self):
        s = tree({A: BLOB_A, B: BLOB_B}) + (
            f"100644 blob {BLOB_CHANGED}\tfour_mode_forecasts/202611080101.json\n"
        )
        # Git tree normally sorts paths; parsing explicitly distinguishes days.
        r = self.check(later=s)
        self.assertEqual(r["newly_visible_count"], 0)
        self.assertEqual(r["changed_same_race_source_git_blob_count"], 0)

    def test_exact_same_commit_cannot_change_blob(self):
        with self.assertRaisesRegex(ValueError, "immutable_commit_blob_drift_impossible"):
            self.check(sha=INITIAL_SHA, later=tree({A: BLOB_CHANGED, B: BLOB_B}))

    def test_non_descendant_or_malformed_ref_refused(self):
        for sha, descendant in ((LATER_SHA, False), ("main", True)):
            with self.subTest(sha=sha), self.assertRaises(ValueError):
                self.check(sha=sha, descendant=descendant)

    def test_forged_formal_fields_are_not_accepted(self):
        for key in ("formal", "independent_first_receipt_verified", "prospective_validation"):
            obj = batch()
            obj[key] = True
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.check(manifest=obj)

    def test_checked_git_ancestry_and_two_immutable_trees_only(self):
        calls = []
        def fake(argv, **kwargs):
            calls.append(argv)
            if argv[1] == "merge-base":
                return subprocess.CompletedProcess(argv, 0, "", "")
            if argv[3] == INITIAL_SHA:
                return subprocess.CompletedProcess(argv, 0,
                                                   tree({A: BLOB_A, B: BLOB_B}), "")
            self.assertEqual(argv[3], LATER_SHA)
            return subprocess.CompletedProcess(argv, 0,
                                               tree({A: BLOB_CHANGED, B: BLOB_B, C: BLOB_C}), "")
        out = d.audit_git(batch(), LATER_SHA, run=fake)
        self.assertEqual(out["changed_same_race_source_git_blob_codes"], [A])
        self.assertEqual(out["newly_visible_race_codes"], [C])
        self.assertEqual([x[1] for x in calls], ["merge-base", "ls-tree", "ls-tree"])
        self.assertTrue(all("confirmed_results" not in " ".join(x) for x in calls))

    def test_failed_ancestry_never_reads_either_tree(self):
        calls = []
        def fake(argv, **kwargs):
            calls.append(argv)
            return subprocess.CompletedProcess(argv, 1, "", "")
        with self.assertRaisesRegex(ValueError, "later_commit_not_verified_descendant"):
            d.audit_git(batch(), LATER_SHA, run=fake)
        self.assertEqual(len(calls), 1)

    def test_original_or_later_git_tree_failure_blocks_report(self):
        for failed_ref in (INITIAL_SHA, LATER_SHA):
            def fake(argv, **kwargs):
                if argv[1] == "merge-base":
                    return subprocess.CompletedProcess(argv, 0, "", "")
                return subprocess.CompletedProcess(argv, 1 if argv[3] == failed_ref else 0,
                                                   tree({A: BLOB_A, B: BLOB_B}), "")
            with self.subTest(ref=failed_ref), self.assertRaisesRegex(
                    ValueError, "unavailable_immutable_git_tree"):
                d.audit_git(batch(), LATER_SHA, run=fake)

    def test_invalid_commit_ref_fails_before_git_execution(self):
        def never(*a, **k):
            self.fail("no git calls permitted")
        with self.assertRaisesRegex(ValueError, "invalid_commit_ref"):
            d.audit_git(batch(), "refs/heads/main", run=never)


if __name__ == "__main__":
    unittest.main()
