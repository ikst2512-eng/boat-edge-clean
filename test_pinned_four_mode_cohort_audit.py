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

    def test_real_roster_drift_is_not_model_gain(self):
        report = run()
        self.assertEqual(report["status"], "historical_complete")
        drift = report["roster_drift_decomposition"]
        self.assertEqual(drift["shared_races"], 86)
        self.assertEqual(drift["prior_only_races"], 34)
        self.assertEqual(drift["rolling_only_races"], 34)
        self.assertEqual(drift["same_calendar_days_prior_vs_holdout"],
                         ["20261028", "20261029", "20261030"])
        for mode in PROOF:
            # The manifest groups have independent roster hashes.
            self.assertEqual(len(report["cohorts"][mode]["expected_race_codes_sha256"]), 64)
        for mode in ("narrow", "hit", "balance", "hole"):
            for top in ("top1", "top3", "top5", "top10"):
                line = drift["by_mode"][mode][top]
                old_total = report["cohorts"]["prior_120"]["topn_hits_on_comparable_only"][mode][top]
                new_total = report["cohorts"]["rolling_120"]["topn_hits_on_comparable_only"][mode][top]
                self.assertEqual(new_total - old_total,
                                 line["observed_delta_due_to_membership"])
                self.assertEqual(old_total, line["shared_86_hits"] + line["removed_34_hits"])
                self.assertEqual(new_total, line["shared_86_hits"] + line["added_34_hits"])

    def test_missing_results_withhold_all_pcts(self):
        # Missing archives are explicitly excluded, never automatically counted as losses.
        with tempfile.TemporaryDirectory() as folder:
            report = run(root=Path(folder))
            self.assertEqual(report["status"], "incomplete_historical_evidence")
            self.assertFalse(report["formal"])
            self.assertIsNone(report["roster_drift_decomposition"])
            for group in report["cohorts"].values():
                self.assertEqual(group["comparable"], 0)
                self.assertIsNone(group["historical_topn_pct"])
                self.assertEqual(len(group["unavailable_codes"]), group["requested"])
                self.assertIsNone(group["pairwise_topn"])


if __name__ == "__main__":
    unittest.main()
