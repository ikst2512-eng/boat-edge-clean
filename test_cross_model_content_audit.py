import unittest
from pathlib import Path
from unittest.mock import patch
from scripts.cross_model_content_audit import audit, extract_top10


class CrossModelAuditTests(unittest.TestCase):
    def test_code_does_not_comment_out_clean_prefixes(self):
        source = Path("scripts/cross_model_content_audit.py").read_text(encoding="utf-8")
        self.assertIn('    clean_prefixes = ("prospective_predictions/",)', source)
        self.assertNotIn(r"\n    clean_prefixes", source)

    def test_no_automatic_import_or_deletion_for_distinct_models(self):
        doc = {
            "schema": "CLEAN_LEGACY_RACE_CROSSWALK_V2",
            "legacy_repo": "old/repo", "clean_repo": "new/repo",
            "legacy_tree_sha": "old-tree", "clean_tree_sha": "new-tree",
            "matched_races": [{
                "race_code": "202610290101",
                "legacy": [{"path": "old.json", "git_blob_sha1": "old", "category": "data/site_prediction_snapshots/"}],
                "clean": [{"path": "new.json", "git_blob_sha1": "new", "category": "prospective_predictions/"}],
            }],
        }
        def fake_inspect(repo, entry):
            return {"path": entry["path"], "sha256": repo,
                    "models": ["SITE_REFERENCE_V122"] if repo == "old/repo"
                    else ["clean-prospective-national-beta0.4-v1"],
                    "top10": None}
        with patch("scripts.cross_model_content_audit.inspect", side_effect=fake_inspect):
            result = audit(doc)
        record = result["races"][0]
        self.assertEqual(record["decision"], "TICKETS_UNCOMPARABLE_MODELS_DISTINCT")
        self.assertTrue(record["models_distinct"])
        self.assertFalse(record["tickets_compared"])
        self.assertFalse(record["copy_authorized"])
        self.assertFalse(record["delete_authorized"])
        self.assertEqual(result["content_read_race_count"], 1)
        self.assertEqual(result["compared_race_count"], 0)
        self.assertEqual(result["tickets_uncomparable_count"], 1)
        self.assertEqual(record["top10_comparisons"], [])
        self.assertFalse(record["historical_evidence_required_proven"])

    def test_does_not_guess_top10_from_ambiguous_predictions(self):
        self.assertIsNone(extract_top10({"predictions": ["1-2-3"] * 10}))
        self.assertIsNone(extract_top10({"top10": ["1-2-3"] * 10}))

    def test_real_clean_prospective_schema_is_ranked(self):
        picks = ["2-1-3", "1-2-4", "2-1-4", "1-2-3", "1-3-2",
                 "1-3-5", "2-3-1", "3-1-4", "2-1-5", "2-3-4"]
        self.assertEqual(extract_top10({"model_version": "clean-prospective-national-beta0.4-v1",
                                        "predictions": picks}), picks)

    def test_four_mode_is_not_falsely_compared_to_prospective(self):
        doc = {"schema": "CLEAN_LEGACY_RACE_CROSSWALK_V2",
               "legacy_repo": "old/repo", "clean_repo": "new/repo",
               "legacy_tree_sha": "a", "clean_tree_sha": "b",
               "matched_races": [{
                   "race_code": "202610290101",
                   "legacy": [{"path": "legacy.json", "git_blob_sha1": "old",
                               "category": "data/site_prediction_snapshots/"}],
                   "clean": [{"path": "four_mode.json", "git_blob_sha1": "new",
                              "category": "four_mode_forecasts/"}],
               }]}
        with patch("scripts.cross_model_content_audit.inspect",
                   return_value={"path": "legacy.json", "sha256": "old",
                                 "models": [], "top10": None}):
            result = audit(doc)
        self.assertEqual(result["compared_race_count"], 0)
        self.assertEqual(result["races"][0]["decision"], "NO_COMPARABLE_FORECAST_EVIDENCE")

    def test_fetch_failure_is_not_misreported_as_missing_evidence(self):
        doc = {
            "schema": "CLEAN_LEGACY_RACE_CROSSWALK_V2",
            "legacy_repo": "old/repo", "clean_repo": "new/repo",
            "legacy_tree_sha": "a", "clean_tree_sha": "b",
            "matched_races": [{
                "race_code": "202610290101",
                "legacy": [{"path": "old.json", "git_blob_sha1": "old",
                            "category": "data/site_prediction_snapshots/"}],
                "clean": [{"path": "new.json", "git_blob_sha1": "new",
                           "category": "prospective_predictions/"}],
            }],
        }
        with patch("scripts.cross_model_content_audit.inspect", side_effect=OSError("unavailable")):
            result = audit(doc)
        self.assertEqual(result["races"][0]["decision"], "REVIEW_FETCH_ERRORS")
        self.assertEqual(result["compared_race_count"], 0)
        self.assertEqual(result["unresolved_count"], 1)

    def test_empty_candidates_are_not_successfully_proven(self):
        doc = {"schema": "CLEAN_LEGACY_RACE_CROSSWALK_V2",
               "legacy_tree_sha": "a", "clean_tree_sha": "b",
               "matched_races": []}
        result = audit(doc)
        self.assertEqual(result["candidate_count"], 0)
        self.assertFalse(result["delete_authorized"])


if __name__ == "__main__":
    unittest.main()
