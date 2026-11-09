"""Nonformal three-original pinned Git replay: strict unit tests, no network."""
import unittest

from scripts.audit_t12_saved_three_original_replay import audit, classify

RACE = "202611030112"
OBS = "ext20261103T08003263231e6e"
SHA = "d0ed89f146dff117021c2bc042b20259d6715515"
REPO = "ikst2512-eng/boat-edge-clean"
MISSING = [
    "exhibition_six_courses",
    "exhibition_times_six",
    "tilt_six",
    "start_exhibition_six",
]


def result(**changes):
    row = {
        "race_code": RACE,
        "observation_id": OBS,
        "evidence_commit": SHA,
        "status": "independent_originals_reaudited",
        "original_files_found": 6,
        "full_t12_source_certified": False,
        "forecast_usable": False,
        "research_complete": False,
        "missing_components": list(MISSING),
        "cutoff_jst": "2026-11-03T20:19:00+09:00",
        "latest_original_received_jst": "2026-11-03T17:00:59.946462+09:00",
        "t12_receipt_margin_seconds": 11880.053538,
    }
    row.update(changes)
    return row


class IndependentImmutableNov3OriginalSource(unittest.TestCase):
    def test_real_archive_component_deficiency_is_preserved(self):
        report = classify(result(), RACE, OBS, SHA)
        self.assertEqual(report["missing_source_components"], sorted(MISSING))
        self.assertEqual(report["original_receipt_margin_seconds"], 11880.054)
        self.assertTrue(report["source_received_by_t12"])
        self.assertFalse(report["source_research_components_complete"])
        self.assertEqual(report["qualified_three_source_candidates"], 0)
        self.assertFalse(report["formal"])
        self.assertFalse(report["accuracy_scoring_allowed"])
        self.assertIsNone(report["formal_accuracy_denominator"])

    def test_unchanged_immutable_git_commit_is_given_to_reauditor(self):
        calls = []
        def replay(repo, token, commit, race, obs):
            calls.append((repo, token, commit, race, obs))
            return result()
        report = audit(REPO, "token", SHA, RACE, OBS, reauditor=replay)
        self.assertEqual(calls, [(REPO, "token", SHA, RACE, OBS)])
        self.assertTrue(report["source_git_blob_and_manifest_hashes_reaudited"])
        self.assertFalse(report["model_original_bytes_consumption_independently_verified"])

    def test_even_complete_three_source_not_formally_certified(self):
        x = classify(result(research_complete=True,
                            missing_components=[]), RACE, OBS, SHA)
        self.assertEqual(x["qualified_three_source_candidates"], 1)
        self.assertFalse(x["independent_first_forecast_git_remote_acceptance_verified"])
        self.assertFalse(x["final_entry_independently_verified"])
        self.assertFalse(x["formal"])
        self.assertFalse(x["forecast_usable"])
        self.assertEqual(x["new_formal_certifications"], 0)

    def test_malformed_or_unreplayed_source_outcome_is_rejected(self):
        for change in (
            {"status": "report_only"},
            {"original_files_found": 5},
            {"full_t12_source_certified": True},
            {"forecast_usable": True},
            {"race_code": "202611030113"},
            {"observation_id": "other"},
            {"evidence_commit": "e"*40},
        ):
            with self.subTest(change=change), self.assertRaises(ValueError):
                classify(result(**change), RACE, OBS, SHA)

    def test_declared_complete_disagreement_is_rejected(self):
        for change in (
            {"research_complete": True},
            {"research_complete": 1},
            {"missing_components": []},
            {"missing_components": ["tilt_six", "tilt_six"]},
            {"missing_components": [None]},
            {"missing_components": "tilt_six"},
            {"missing_components": [1]},
        ):
            with self.subTest(change=change), self.assertRaises(ValueError):
                classify(result(**change), RACE, OBS, SHA)

    def test_false_receipt_margin_is_rejected(self):
        for change in (
            {"t12_receipt_margin_seconds": 11881},
            {"t12_receipt_margin_seconds": True},
            {"t12_receipt_margin_seconds": float("nan")},
            {"t12_receipt_margin_seconds": None},
            {"t12_receipt_margin_seconds": "11880.053538"},
        ):
            with self.subTest(change=change), self.assertRaises(ValueError):
                classify(result(**change), RACE, OBS, SHA)

    def test_unknown_and_cross_day_receipt_is_rejected(self):
        for change in (
            {"cutoff_jst": "2026-11-04T20:19:00+09:00"},
            {"latest_original_received_jst": "2026-11-02T17:00:59+09:00"},
            {"cutoff_jst": "2026-11-03T20:19:00Z"},
            {"latest_original_received_jst": "invalid"},
        ):
            with self.subTest(change=change), self.assertRaises(ValueError):
                classify(result(**change), RACE, OBS, SHA)

    def test_late_source_receipt_does_not_count_as_qualified(self):
        x = classify(result(
            latest_original_received_jst="2026-11-03T20:19:05+09:00",
            t12_receipt_margin_seconds=-5,
            research_complete=False,
            missing_components=["odds_received_by_t12"]
        ), RACE, OBS, SHA)
        self.assertFalse(x["source_received_by_t12"])
        self.assertEqual(x["qualified_three_source_candidates"], 0)

    def test_reject_invalid_repo_race_and_observation(self):
        problems = (
            ("/bad", SHA, RACE, OBS), ("../bad", SHA, RACE, OBS),
            ("a/..", SHA, RACE, OBS),
            (REPO, "none", RACE, OBS),
            (REPO, SHA, "202611032512", OBS),
            (REPO, SHA, "202611030113", "bad/obs"),
            (REPO, SHA, "202613030112", OBS),
            (REPO, SHA, RACE, "."),
        )
        for repo, commit, race, obs in problems:
            with self.subTest(value=(repo,commit,race,obs)), self.assertRaises(ValueError):
                audit(repo, "token", commit, race, obs,
                      reauditor=lambda *args: result())

    def test_missing_token_is_not_an_anonymous_success(self):
        with self.assertRaises(ValueError):
            audit(REPO, None, SHA, RACE, OBS,
                  reauditor=lambda *args: result())

    def test_no_forecast_or_final_entry_gate_is_inferred_from_file_presence(self):
        row = classify(result(), RACE, OBS, SHA)
        self.assertFalse(row["model_original_bytes_consumption_independently_verified"])
        self.assertFalse(row["independent_first_forecast_git_remote_acceptance_verified"])
        self.assertFalse(row["final_entry_independently_verified"])
        self.assertFalse(row["formal"])
        self.assertFalse(row["t12_eligible"])


if __name__ == "__main__":
    unittest.main()
