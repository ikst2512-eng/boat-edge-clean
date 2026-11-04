"""Regression and provenance tests for immutable historical research rosters."""
import json
import tempfile
import unittest
from pathlib import Path

from pinned_four_mode_cohort_audit import load_locked_manifest, run, MANIFEST, PROOF, roster_digest


class FrozenCohortTests(unittest.TestCase):
    def test_original_research_rosters_and_overlap(self):
        data, digest = load_locked_manifest()
        self.assertEqual(len(digest), 64)
        self.assertEqual(data["expected_overlaps"],
                         {"prior_holdout": 0, "rolling_holdout": 0, "prior_rolling": 86})
        for name, (n, expected_sha, _run, _artifact, _field) in PROOF.items():
            codes = data["cohorts"][name]["codes"]
            self.assertEqual(len(codes), n)
            self.assertEqual(roster_digest(codes), expected_sha)

    def assert_bad_manifest(self, modification, expected_error):
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
        modification(data)
        with tempfile.TemporaryDirectory() as folder:
            filename = Path(folder) / "altered.json"
            filename.write_text(json.dumps(data, sort_keys=True), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, expected_error):
                load_locked_manifest(filename)

    def test_corrupted_race_roster_blocked(self):
        def modify(data):
            data["cohorts"]["prior_120"]["codes"][0] = "202610280104"
            data["cohorts"]["prior_120"]["codes"].sort()
        self.assert_bad_manifest(modify, "roster_provenance_or_hash_mismatch")

    def test_missing_member_blocked(self):
        def modify(data):
            data["cohorts"]["holdout_240"]["codes"].pop()
        self.assert_bad_manifest(modify, "invalid_roster_membership")

    def test_duplicate_race_blocked(self):
        def modify(data):
            codes = data["cohorts"]["rolling_120"]["codes"]
            codes[1] = codes[0]
        self.assert_bad_manifest(modify, "invalid_roster_membership")

    def test_forged_formal_claim_blocked(self):
        self.assert_bad_manifest(lambda d: d.__setitem__("formal", True),
                                 "invalid_manifest_contract")

    def test_changed_source_run_blocked(self):
        self.assert_bad_manifest(
            lambda d: d["cohorts"]["prior_120"].__setitem__("actions_run_id", 1),
            "roster_provenance_or_hash_mismatch")

    def test_missing_results_withhold_all_pcts(self):
        # Missing archives are explicitly excluded, never automatically counted as losses.
        with tempfile.TemporaryDirectory() as folder:
            report = run(root=Path(folder))
            self.assertEqual(report["status"], "incomplete_historical_evidence")
            self.assertFalse(report["formal"])
            for group in report["cohorts"].values():
                self.assertEqual(group["comparable"], 0)
                self.assertIsNone(group["historical_topn_pct"])
                self.assertEqual(len(group["unavailable_codes"]), group["requested"])
                self.assertIsNone(group["pairwise_topn"])


if __name__ == "__main__":
    unittest.main()
