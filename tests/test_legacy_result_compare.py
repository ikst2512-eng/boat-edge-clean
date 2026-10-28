import json
import unittest

from scripts.legacy_result_compare import compare_record, classify_missing_pair


class LegacyComparisonTests(unittest.TestCase):
    def build(self, order, clean=False):
        fields = {"finish_order": order}
        fields["race_code" if clean else "race_key"] = (
            "202610270101" if clean else "20261027-01-01")
        return json.dumps(fields).encode()

    def test_matching_order_not_deletion_permission(self):
        result = compare_record("202610270101", self.build([3, 4, 1]),
                                self.build([3, 4, 1], True))
        self.assertEqual(result["status"], "FINISH_ORDER_MATCH")
        self.assertFalse(result["delete_authorized"])
        self.assertFalse(result["prediction_equivalence_verified"])
        self.assertEqual(len(result["legacy_sha256"]), 64)

    def test_conflict(self):
        result = compare_record("202610270101", self.build([3, 4, 1]),
                                self.build([1, 3, 4], True))
        self.assertEqual(result["status"], "FINISH_ORDER_CONFLICT")

    def test_bad_race_identity(self):
        with self.assertRaises(ValueError):
            compare_record("202610270104", self.build([3, 4, 1]),
                           self.build([3, 4, 1], True))

    def test_missing_pair_pending(self):
        result = classify_missing_pair("202610280306",
            json.dumps({"race_key": "20261028-03-06", "status": "pending"}).encode())
        self.assertEqual(result["status"], "LEGACY_PENDING_CLEAN_RESULT_MISSING")
        self.assertFalse(result["delete_authorized"])

    def test_missing_pair_trifecta_not_established(self):
        result = classify_missing_pair("202610280112",
            json.dumps({"race_key": "20261028-01-12",
                        "status": "trifecta_not_established", "finish_order": []}).encode())
        self.assertEqual(result["status"], "LEGACY_TRIFECTA_NOT_ESTABLISHED")
        self.assertFalse(result["source_equivalence_verified"])

    def test_missing_pair_wrong_identity_rejected(self):
        with self.assertRaises(ValueError):
            classify_missing_pair("202610280112",
                json.dumps({"race_key": "20261028-01-11", "status": "pending"}).encode())

    def test_invalid_finish_order(self):
        result = compare_record("202610270101", self.build([3, 3, 1]),
                                self.build([3, 3, 1], True))
        self.assertEqual(result["status"], "INVALID_OR_MISSING_FINISH_ORDER")


if __name__ == "__main__":
    unittest.main()
