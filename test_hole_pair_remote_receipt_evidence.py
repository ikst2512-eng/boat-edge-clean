"""Adversarial tests: GitHub readback is never first-receipt proof."""
import hashlib
import json
import unittest
from datetime import datetime, timedelta, timezone

import hole_pair_remote_receipt_evidence as s

BASE = [
    "1-2-3", "1-2-4", "1-3-2", "1-3-4", "2-1-3",
    "2-1-4", "1-4-2", "1-4-3", "2-3-1", "2-3-4",
]


def candidate():
    choices = {name: list(BASE) for name in s.ARMS}
    return {
        "schema": "HOLE_PAIR_FUTURE_FREEZE_V1",
        "status": "locally_frozen_unverified",
        "method": "HOLE_PAIR_NOV06_LOCKED_RESEARCH_V1",
        "method_source_sha256": s.LOCKED_METHOD_SHA256,
        "race_code": "202611090101",
        "source_sha256": "a" * 64,
        "candidates": choices,
        "candidates_sha256": hashlib.sha256(
            json.dumps(choices, sort_keys=True, ensure_ascii=False,
                       separators=(",", ":")).encode()).hexdigest(),
        "local_start_jst": "2026-11-09T10:50:00+09:00",
        "local_finish_jst": "2026-11-09T10:51:00+09:00",
        "t_minus_12_jst": "2026-11-09T11:00:00+09:00",
        "deadline_jst": "2026-11-09T11:12:00+09:00",
        "formal": False,
        "prospective_validation": False,
        "independent_first_receipt_verified": False,
        "production_forecast_changed": False,
    }


def observed(record, at="2026-11-09T01:55:00+00:00"):
    raw = s.canonical_bytes(record)
    return {
        "kind": "github_api_readback_not_first_receipt",
        "race_code": record["race_code"],
        "candidate_record_sha256": hashlib.sha256(raw).hexdigest(),
        "github_blob_sha1": hashlib.sha1(
            b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest(),
        "remote_bytes": raw,
        "server_observed_at_utc": at,
    }


class ReceiptEvidenceTests(unittest.TestCase):
    def test_missing_observation_not_formally_eligible(self):
        r = s.inspect(candidate())
        self.assertEqual(r["status"], "no_remote_candidate_observation")
        self.assertFalse(r["independent_first_receipt_verified"])
        self.assertFalse(r["formal"])
        self.assertFalse(r["official_t12_complete_verified"])

    def test_matching_early_readback_still_not_first_receipt(self):
        c = candidate()
        r = s.inspect(c, observed(c))
        self.assertEqual(r["status"], "pre_t12_readback_consistent_not_first_receipt")
        self.assertTrue(r["remote_bytes_and_reported_clock_consistent"])
        self.assertFalse(r["independent_first_receipt_verified"])
        self.assertFalse(r["formal"])
        self.assertFalse(r["production_promotion_allowed"])

    def test_conflicting_remote_candidate_or_hash_rejected(self):
        c = candidate()
        o = observed(c)
        o["remote_bytes"] += b" "
        with self.assertRaisesRegex(ValueError, "remote_candidate_bytes_conflict"):
            s.inspect(c, o)
        o = observed(c)
        o["candidate_record_sha256"] = "b" * 64
        with self.assertRaisesRegex(ValueError, "remote_sha256_or_git_blob_conflict"):
            s.inspect(c, o)

    def test_unknown_claim_of_independent_first_receipt_rejected(self):
        c = candidate()
        o = observed(c)
        o["independent_first_receipt_verified"] = True
        with self.assertRaisesRegex(ValueError, "untrusted_observation_fields_or_claim"):
            s.inspect(c, o)
        o = observed(c)
        o["kind"] = "independently_first_received"
        with self.assertRaisesRegex(ValueError, "observation_identity_or_claim_invalid"):
            s.inspect(c, o)

    def test_late_and_ambiguous_github_observation_not_counted(self):
        c = candidate()
        for when in ("2026-11-09T02:00:00+00:00",
                     "2026-11-09T01:59:59+00:00",
                     "2026-11-09T02:02:00+00:00"):
            r = s.inspect(c, observed(c, when))
            self.assertEqual(r["status"], "readback_late_or_same_second")
            self.assertFalse(r["remote_bytes_and_reported_clock_consistent"])

    def test_remote_readback_before_local_creation_rejected(self):
        c = candidate()
        with self.assertRaisesRegex(ValueError, "reported_observation_precedes_candidate_finish"):
            s.inspect(c, observed(c, "2026-11-09T01:50:59+00:00"))
        with self.assertRaisesRegex(ValueError, "reported_observation_precedes_candidate_finish"):
            s.inspect(c, observed(c, "2026-11-09T01:51:01+00:00"))

    def test_altered_original_candidate_or_wrong_cutoff_refused(self):
        c = candidate()
        c["candidates"]["baseline"][0] = "6-5-4"
        with self.assertRaisesRegex(ValueError, "candidate_digest_mismatch"):
            s.inspect(c)
        c = candidate()
        c["local_finish_jst"] = "2026-11-09T11:00:00+09:00"
        with self.assertRaisesRegex(ValueError, "candidate_timeline_invalid"):
            s.inspect(c)
        c = candidate()
        c["method_source_sha256"] = "b" * 64
        with self.assertRaisesRegex(ValueError, "untrusted_candidate_claim_or_method"):
            s.inspect(c)

    def test_past_inspected_races_not_eligible_for_nov9_holdout(self):
        c = candidate()
        c["race_code"] = "202611080101"
        with self.assertRaisesRegex(ValueError, "not_future_protocol_eligible"):
            s.inspect(c)

    def test_duplicate_or_orphan_receipt_does_not_change_denominator(self):
        c = candidate()
        with self.assertRaisesRegex(ValueError, "duplicate_frozen_race"):
            s.inspect_batch([c, c], {})
        with self.assertRaisesRegex(ValueError, "orphan_remote_observation"):
            s.inspect_batch([c], {"202611090102": observed(c)})
        output = s.inspect_batch([c], {c["race_code"]: observed(c)})
        self.assertEqual(output["examined"], 1)
        self.assertEqual(output["pre_t12_readback_consistent"], 1)
        self.assertEqual(output["independent_first_receipt_verified"], 0)
        self.assertEqual(output["formally_eligible"], 0)


if __name__ == "__main__":
    unittest.main()
