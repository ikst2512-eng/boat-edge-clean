"""Offline adversarial tests: matching D1 JSON is not external attestation."""
import unittest

from research import hole_pair_d1_receipt_chain_audit as a
from test_hole_pair_remote_receipt_evidence import candidate


def claimed_receipt(c):
    return {
        "schema": a.RECEIPT_SCHEMA,
        "race_code": c["race_code"],
        "candidate_sha256": a.sha256(a.canonical_bytes(c)).hexdigest(),
        "declared_cutoff_utc": "2026-11-09T02:00:00.000Z",
        "first_received_at_utc": "2026-11-09T01:55:00.000Z",
        "already_recorded": False,
        "timestamp_origin": a.TIMESTAMP_ORIGIN,
        "independent_server_acceptance_observed": True,
        "independent_first_receipt_verified": False,
        "official_t12_complete_verified": False,
        "formal": False,
        "production_promotion_allowed": False,
        "warning": a.WORKER_WARNING,
    }


class D1ReceiptChainAuditTests(unittest.TestCase):
    def test_absence_cannot_be_converted_to_hit_miss_or_formal(self):
        r = a.audit_one(candidate())
        self.assertEqual(r["status"], "no_receiver_receipt")
        self.assertFalse(r["formally_eligible"])
        self.assertFalse(r["official_t12_complete_verified"])
        self.assertFalse(r["model_improvement_proven"])

    def test_matching_claim_must_stay_nonformal(self):
        c = candidate()
        r = a.audit_one(c, claimed_receipt(c))
        self.assertTrue(r["claimed_receiver_receipt_consistent"])
        self.assertFalse(r["receiver_receipt_authenticated"])
        self.assertFalse(r["original_source_independently_verified"])
        self.assertFalse(r["independent_first_receipt_verified"])
        self.assertFalse(r["formally_eligible"])
        self.assertFalse(r["production_promotion_allowed"])

    def test_claim_of_formal_or_official_proof_rejected(self):
        c = candidate()
        for field in ("formal", "production_promotion_allowed",
                      "independent_first_receipt_verified",
                      "official_t12_complete_verified"):
            r = claimed_receipt(c)
            r[field] = True
            with self.subTest(field=field), self.assertRaisesRegex(
                    ValueError, "conflicting_d1_receipt_identity_or_claim"):
                a.audit_one(c, r)

    def test_extra_first_acceptance_or_official_proof_flag_rejected(self):
        c = candidate()
        r = claimed_receipt(c)
        r["official_120_odds_verified"] = True
        with self.assertRaisesRegex(ValueError, "unknown_receipt_fields_or_forged_proof"):
            a.audit_one(c, r)

    def test_candidate_identity_and_method_must_match(self):
        c = candidate()
        r = claimed_receipt(c)
        r["candidate_sha256"] = "b" * 64
        with self.assertRaisesRegex(ValueError, "conflicting_d1_receipt_identity_or_claim"):
            a.audit_one(c, r)
        r = claimed_receipt(c)
        r["race_code"] = "202611090102"
        with self.assertRaisesRegex(ValueError, "conflicting_d1_receipt_identity_or_claim"):
            a.audit_one(c, r)

    def test_cutoff_and_receipt_time_must_be_strict(self):
        c = candidate()
        for t, message in (
            ("2026-11-09T01:51:00.000Z", "receipt_precedes_candidate"),
            ("2026-11-09T01:51:01.000Z", "receipt_precedes_candidate"),
            ("2026-11-09T01:59:58.000Z", "late_or_ambiguous"),
            ("2026-11-09T02:00:00.000Z", "late_or_ambiguous"),
        ):
            r = claimed_receipt(c)
            r["first_received_at_utc"] = t
            with self.subTest(t=t), self.assertRaisesRegex(ValueError, message):
                a.audit_one(c, r)
        r = claimed_receipt(c)
        r["declared_cutoff_utc"] = "2026-11-10T02:00:00.000Z"
        with self.assertRaisesRegex(ValueError, "declared_cutoff_mismatch"):
            a.audit_one(c, r)

    def test_invalid_time_or_timezone_fails_closed(self):
        c = candidate()
        for t in ("2026-11-09T01:55:00", "2026-11-09T10:55:00+09:00",
                  "not a time", "2026-11-09T01:55:00+02:00"):
            r = claimed_receipt(c)
            r["first_received_at_utc"] = t
            with self.subTest(t=t), self.assertRaisesRegex(ValueError, "invalid_claimed_utc"):
                a.audit_one(c, r)

    def test_noncanonical_worker_timestamps_are_rejected(self):
        c = candidate()
        # The Worker returns exactly YYYY-MM-DDTHH:MM:SS.mmmZ.
        malformed = (
            "2026-11-09T01:55:00Z",
            "2026-11-09T01:55:00+00:00",
            "2026-11-09T01:55:00.0Z",
            "2026-11-09T01:55:00.0000Z",
            "2026-11-09T01:55:00.000+00:00",
            "2026-11-09T01:55:00.000+09:00",
            "2026-11-09T01:55:00.000000Z",
        )
        for field in ("first_received_at_utc", "declared_cutoff_utc"):
            for value in malformed:
                receipt = claimed_receipt(c)
                receipt[field] = value
                with self.subTest(field=field, value=value):
                    with self.assertRaisesRegex(ValueError, "invalid_claimed_utc"):
                        a.audit_one(c, receipt)

    def test_worker_warning_must_match_exact_transport_contract(self):
        c = candidate()
        for warning in (
            "Winner was 1-2-3",
            "Independently verified first receipt.",
            "Self-reported storage time is not independently signed.",
            "",
            None,
        ):
            receipt = claimed_receipt(c)
            receipt["warning"] = warning
            with self.subTest(warning=warning):
                with self.assertRaisesRegex(
                        ValueError, "conflicting_d1_receipt_identity_or_claim"):
                    a.audit_one(c, receipt)

    def test_fixed_transport_warning_remains_nonformal(self):
        c = candidate()
        receipt = claimed_receipt(c)
        self.assertEqual(receipt["warning"], a.WORKER_WARNING)
        result = a.audit_one(c, receipt)
        self.assertTrue(result["claimed_receiver_receipt_consistent"])
        self.assertFalse(result["receiver_receipt_authenticated"])
        self.assertFalse(result["formally_eligible"])

    def test_repeat_does_not_add_independent_receipt(self):
        c = candidate()
        r = claimed_receipt(c)
        r["already_recorded"] = True
        x = a.audit_one(c, r)
        self.assertTrue(x["already_recorded"])
        self.assertFalse(x["independent_first_receipt_verified"])

    def test_duplicate_and_orphan_do_not_expand_denominator(self):
        c = candidate()
        with self.assertRaisesRegex(ValueError, "duplicate_frozen_race"):
            a.audit_batch([c, c], {})
        with self.assertRaisesRegex(ValueError, "orphan_or_invalid_receiver_receipt"):
            a.audit_batch([c], {"202611090102": claimed_receipt(c)})
        r = a.audit_batch([c], {c["race_code"]: claimed_receipt(c)})
        self.assertEqual(r["examined"], 1)
        self.assertEqual(r["self_reported_clock_consistent"], 1)
        self.assertEqual(r["formally_eligible"], 0)
        self.assertEqual(r["independent_first_receipt_verified"], 0)

    def test_no_results_needed_for_receipt_chain(self):
        c = candidate()
        self.assertNotIn("finish_order", c)
        r = a.audit_batch([c], {})
        self.assertEqual(r["missing_receiver_receipt"], 1)
        self.assertFalse(r["formal"])


if __name__ == "__main__":
    unittest.main()
