import unittest
from scripts.legacy_payout_evidence import build_ledger


class PayoutEvidenceTests(unittest.TestCase):
    def report(self, **overrides):
        row = {"status": "FINISH_ORDER_MATCH", "race_code": "202610270101",
               "legacy_payout_yen_per_100": 12320,
               "legacy_sha256": "a" * 64,
               "legacy_path": "data/site_results/20261027-01-01.json"}
        row.update(overrides)
        return {"schema": "CLEAN_LEGACY_RESULT_COMPARISON_V1", "records": [row],
                "legacy_tree_sha": "legacy_tree", "clean_tree_sha": "clean_tree",
                "compared": 1}

    def test_positive_payout_provenance(self):
        ledger = build_ledger(self.report())
        self.assertEqual(ledger["payout_record_count"], 1)
        self.assertFalse(ledger["delete_authorized"])
        self.assertFalse(ledger["records"][0]["verified_against_official_source"])

    def test_unknown_payout_excluded(self):
        self.assertEqual(build_ledger(self.report(legacy_payout_yen_per_100=None))
                         ["payout_record_count"], 0)

    def test_conflicts_excluded(self):
        self.assertEqual(build_ledger(self.report(status="FINISH_ORDER_CONFLICT"))
                         ["payout_record_count"], 0)

    def test_wrong_source_path_rejected(self):
        with self.assertRaises(ValueError):
            build_ledger(self.report(legacy_path="../results.json"))


if __name__ == "__main__":
    unittest.main()
