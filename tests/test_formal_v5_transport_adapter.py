"""Synthetic transport adapter tests; no actual model or results."""
import json
import unittest
from itertools import permutations
from formal_candidate_validator import InvalidCandidate
from formal_v5_transport_adapter import inspect_v5_transport


def case():
    return {"race_code": "20261028" + "01" + "01",
            "validated": True, "model_version": "V1.21.20",
            "probabilities": {"-".join(t): 1 / 120 for t in permutations("123456", 3)}}


class TransportAdapterTests(unittest.TestCase):
    def test_transport_never_approves(self):
        result = inspect_v5_transport(json.dumps(case()).encode())
        self.assertEqual(result["race_key"], "20261028-01-01")
        self.assertFalse(result["model_authenticity_verified"])
        self.assertFalse(result["formal_approved"])

    def test_duplicate_json_rejected(self):
        raw = json.dumps(case()).replace('"validated":', '"race_code":"202610280201","validated":')
        with self.assertRaises(InvalidCandidate):
            inspect_v5_transport(raw.encode())

    def test_missing_combo_rejected(self):
        obj = case()
        obj["probabilities"].pop(next(iter(obj["probabilities"])))
        with self.assertRaises(InvalidCandidate):
            inspect_v5_transport(json.dumps(obj).encode())

    def test_untrusted_proof_rejected(self):
        obj = case()
        obj["freeze_proof"] = {"validated": True}
        with self.assertRaises(InvalidCandidate):
            inspect_v5_transport(json.dumps(obj).encode())

    def test_embedded_approval_claims_rejected(self):
        for field in ("formal_approved", "model_authenticity_verified",
                      "independent_receipt_verified", "input_provenance_verified",
                      "independent_github_arrival_verified", "result_unlock_token",
                      "freeze_proof"):
            with self.subTest(field=field):
                obj = case()
                obj[field] = False
                with self.assertRaises(InvalidCandidate):
                    inspect_v5_transport(json.dumps(obj).encode())

    def test_nonfinite_probability_rejected(self):
        obj = case()
        first = next(iter(obj["probabilities"]))
        obj["probabilities"][first] = float("nan")
        with self.assertRaises(InvalidCandidate):
            inspect_v5_transport(json.dumps(obj).encode())


if __name__ == "__main__":
    unittest.main()
