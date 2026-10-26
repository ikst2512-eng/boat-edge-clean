"""Synthetic-only provenance audit tests."""
import copy
import unittest
from research_provenance_audit import canonical_digest, audit_envelope, make_comparison
from research_paired_evaluation import TICKETS

def fixture():
    p = {t: 1.0 / 120 for t in TICKETS}
    m = {"model_sha": "a" * 40, "input_sha256": "b" * 64,
         "probabilities": p, "probabilities_sha256": canonical_digest(p),
         "source_received_at": "2026-10-27T09:00:00+09:00",
         "generated_at": "2026-10-27T09:01:00+09:00"}
    return {"race_code": "202610271201", "cutoff_jst": "2026-10-27T09:12:00+09:00",
            "actual": "1-2-3", "baseline": copy.deepcopy(m), "candidate": copy.deepcopy(m)}

class ProvenanceTests(unittest.TestCase):
    def test_metadata_cannot_self_certify(self):
        row, audit = make_comparison(fixture())
        self.assertEqual(len(row["baseline"]), 120)
        self.assertFalse(audit["prospective_verified"])

    def test_modified_distribution_blocked(self):
        x = fixture()
        x["candidate"]["probabilities"]["1-2-3"] += .01
        with self.assertRaisesRegex(ValueError, "digest mismatch"):
            audit_envelope(x)

    def test_postcutoff_blocked(self):
        x = fixture()
        x["candidate"]["generated_at"] = x["cutoff_jst"]
        with self.assertRaisesRegex(ValueError, "late"):
            audit_envelope(x)

    def test_source_after_generation_blocked(self):
        x = fixture()
        x["baseline"]["source_received_at"] = "2026-10-27T09:05:00+09:00"
        with self.assertRaisesRegex(ValueError, "late"):
            audit_envelope(x)

    def test_missing_model_sha_blocked(self):
        x = fixture()
        x["baseline"]["model_sha"] = ""
        with self.assertRaisesRegex(ValueError, "model_sha"):
            audit_envelope(x)

if __name__ == "__main__":
    unittest.main()
