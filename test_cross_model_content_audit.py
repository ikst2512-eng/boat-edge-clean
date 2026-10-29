import unittest
from unittest.mock import patch
from scripts.cross_model_content_audit import audit, extract_top10


class CrossModelAuditTests(unittest.TestCase):
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
        self.assertEqual(record["decision"], "CROSS_MODEL_DISTINCT_NO_IMPORT")
        self.assertFalse(record["copy_authorized"])
        self.assertFalse(record["delete_authorized"])
        self.assertEqual(record["top10_comparisons"], [])
        self.assertFalse(record["historical_evidence_required_proven"])

    def test_does_not_guess_top10_from_ambiguous_predictions(self):
        self.assertIsNone(extract_top10({"predictions": ["1-2-3"] * 10}))
        self.assertIsNone(extract_top10({"top10": ["1-2-3"] * 10}))

    def test_empty_candidates_are_not_successfully_proven(self):
        doc = {"schema": "CLEAN_LEGACY_RACE_CROSSWALK_V2",
               "legacy_tree_sha": "a", "clean_tree_sha": "b",
               "matched_races": []}
        result = audit(doc)
        self.assertEqual(result["candidate_count"], 0)
        self.assertFalse(result["delete_authorized"])


if __name__ == "__main__":
    unittest.main()
