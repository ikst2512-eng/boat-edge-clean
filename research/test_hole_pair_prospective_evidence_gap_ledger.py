"""Synthetic blockers only. No source file, results, network or real forecast."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from research import hole_pair_prospective_evidence_gap_ledger as g
from research.test_hole_pair_cross_batch_roster import (
    DAY, R1, R2, R3, frozen, manifest,
)
from research.test_hole_pair_d1_receipt_chain_audit import claimed_receipt


def one():
    return manifest([R1], [frozen(R1)])


def pointer(code=R1):
    return {
        "race_code": code,
        "upstream_report_sha256_claim": "a" * 64,
        "upstream_report_locator_claim": "github-actions:123/official-source-report",
    }


class ProspectiveEvidenceGapLedgerTests(unittest.TestCase):
    def test_single_missing_receipt_and_source_reference_is_not_formal(self):
        result = g.audit(one())
        self.assertEqual(result["frozen_candidates_inspected"], 1)
        self.assertEqual(result["locally_excluded"], 0)
        self.assertEqual(result["candidate_d1_receipt_missing"], 1)
        self.assertEqual(result["external_source_report_pointer_missing"], 1)
        self.assertEqual(result["prospective_pilot_formally_eligible"], 0)
        self.assertEqual(result["prospective_confirmation_formally_eligible"], 0)
        self.assertFalse(result["accuracy_denominator_authorized"])
        self.assertFalse(result["result_files_read"])
        row = result["rows"][0]
        self.assertEqual(row["d1_receipt_status"], "no_receiver_receipt")
        self.assertIn("d1_receiver_receipt_missing", row["missing_evidence_codes"])
        self.assertIn("same_race_full_120_way_odds_unverified", row["missing_evidence_codes"])
        self.assertIn("source_received_then_prediction_generated_before_t12_unverified",
                      row["missing_evidence_codes"])
        self.assertFalse(row["hit_miss_scoring_allowed"])

    def test_plausible_d1_claim_is_not_a_first_remote_witness(self):
        m = one()
        out = g.audit(m, {R1: claimed_receipt(m["records"][0])})
        self.assertEqual(out["candidate_d1_claim_consistent_only"], 1)
        self.assertEqual(out["candidate_d1_receipt_missing"], 0)
        self.assertEqual(
            out["rows"][0]["d1_receipt_status"],
            "self_reported_d1_timestamp_consistent_not_independent_proof")
        self.assertIn("d1_timestamp_is_self_report_not_independent_witness",
                      out["rows"][0]["missing_evidence_codes"])
        self.assertFalse(out["rows"][0]["independent_first_receipt_verified"])
        self.assertEqual(out["independent_external_witness_authenticated"], 0)

    def test_repeat_receipt_flag_does_not_add_pilot_eligibility(self):
        m = one()
        rec = claimed_receipt(m["records"][0])
        rec["already_recorded"] = True
        r = g.audit(m, {R1: rec})
        self.assertEqual(r["candidate_d1_claim_consistent_only"], 1)
        self.assertEqual(r["prospective_pilot_formally_eligible"], 0)

    def test_same_race_upstream_report_pointer_still_unverified(self):
        r = g.audit(one(), source_report_pointers={R1: pointer()})
        self.assertEqual(r["external_source_report_pointer_claims"], 1)
        self.assertFalse(r["rows"][0]["source_report_pointer_unverified"][
            "external_report_bytes_and_authorship_independently_verified"])
        self.assertIn("external_official_source_audit_reference_unverified",
                      r["rows"][0]["missing_evidence_codes"])
        self.assertEqual(r["official_three_source_t12_verified"], 0)

    def test_no_candidate_with_official_pointer_remains_excluded(self):
        m = manifest([R1, R2], [frozen(R1)], {"after_t_minus_12": [R2]})
        r = g.audit(m, source_report_pointers={R2: pointer(R2)})
        self.assertEqual(r["locally_excluded"], 1)
        self.assertEqual(r["frozen_candidates_inspected"], 1)
        self.assertEqual(r["source_report_pointer_claims_for_excluded"], 1)
        row = next(x for x in r["rows"] if x["race_code"] == R2)
        self.assertEqual(row["classification"], "excluded_before_frozen_candidate")
        self.assertTrue(row["exclusion_must_remain_in_universe_ledger"])
        self.assertIsNone(row["candidate_record_sha256"])

    def test_three_races_mixed_status_counts_by_distinct_source_ids(self):
        m = manifest(
            [R1, R2, R3], [frozen(R1), frozen(R3)],
            {"invalid_deadline": [R2]})
        out = g.audit(
            m, {R1: claimed_receipt(m["records"][0])},
            {R1: pointer(), R2: pointer(R2)})
        self.assertEqual(out["snapshot_forecast_codes_examined"], 3)
        self.assertEqual(out["locally_excluded"], 1)
        self.assertEqual(out["frozen_candidates_inspected"], 2)
        self.assertEqual(out["candidate_d1_receipt_missing"], 1)
        self.assertEqual(out["candidate_d1_claim_consistent_only"], 1)
        self.assertEqual(out["external_source_report_pointer_claims"], 1)
        self.assertEqual(out["external_source_report_pointer_missing"], 1)
        self.assertEqual(out["prospective_confirmation_formally_eligible"], 0)

    def test_empty_main_forecast_snapshot_does_not_become_complete_day(self):
        r = g.audit(manifest([], []))
        self.assertEqual(r["rows"], [])
        self.assertFalse(r["whole_day_schedule_verified"])
        self.assertFalse(r["accuracy_denominator_authorized"])

    def test_cross_race_external_source_reference_rejected(self):
        with self.assertRaisesRegex(ValueError, "source_report_pointer_cross_race"):
            g.audit(one(), source_report_pointers={R1: pointer(R2)})

    def test_orphan_d1_receipt_or_source_reference_rejected(self):
        for receipts, refs in (
            ({R2: {}}, {}),
            ({}, {R2: pointer(R2)}),
            ({R1: {}}, {}),
        ):
            with self.subTest(receipts=receipts, refs=refs), self.assertRaises(ValueError):
                g.audit(one(), receipts, refs)

    def test_excluded_race_cannot_receive_d1_receipt_without_candidate(self):
        m = manifest([R1], [], {"after_t_minus_12": [R1]})
        with self.assertRaisesRegex(ValueError, "orphan_d1_receipt"):
            g.audit(m, {R1: {}})

    def test_invalid_external_report_pointer_schema_and_claims_rejected(self):
        invalids = (
            {**pointer(), "official_t12_verified": True},
            {**pointer(), "upstream_report_sha256_claim": "x"*64},
            {**pointer(), "upstream_report_locator_claim": "../../../bad space"},
            {**pointer(), "race_code": None},
        )
        for value in invalids:
            with self.subTest(value=value), self.assertRaises(ValueError):
                g.audit(one(), source_report_pointers={R1: value})

    def test_forged_d1_formal_or_earlier_timestamp_rejected(self):
        m = one()
        for mode in ("formal", "bad_digest", "late_clock", "fake_auth"):
            rec = claimed_receipt(m["records"][0])
            if mode == "formal":
                rec["formal"] = True
            elif mode == "bad_digest":
                rec["candidate_sha256"] = "0" * 64
            elif mode == "late_clock":
                rec["first_received_at_utc"] = "2026-11-09T02:00:00.000Z"
            else:
                rec["receiver_authentication_proven"] = True
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                g.audit(m, {R1: rec})

    def test_manifest_census_and_forged_future_status_rejected(self):
        for mutation in (
            lambda x: x.update(formal=True),
            lambda x: x.update(prospective_validation=True),
            lambda x: x.update(eligible_forecasts_examined=0),
            lambda x: x.update(frozen_count=0),
            lambda x: x["source_forecast_codes"].append(R2),
            lambda x: x["source_snapshot_coverage"].update(
                pilot_formally_eligible=1),
        ):
            obj = one()
            mutation(obj)
            with self.subTest(mutation=str(mutation)), self.assertRaises(ValueError):
                g.audit(obj)

    def test_canonical_candidate_digest_and_source_binding(self):
        m = one()
        out = g.audit(m)
        row = out["rows"][0]
        self.assertEqual(row["candidate_record_sha256"],
                         g.hashlib.sha256(g.canonical_bytes(m["records"][0])).hexdigest())
        self.assertEqual(row["original_source_sha256_claim"],
                         m["records"][0]["source_sha256"])
        self.assertEqual(row["candidate_method_source_sha256"],
                         m["records"][0]["method_source_sha256"])
        self.assertFalse(row["production_promotion_allowed"])

    def test_cli_loader_refuses_symlinks_and_oversized_inputs(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            original = root / "manifest.json"
            original.write_text(json.dumps(one()))
            self.assertEqual(g._load_file(original)["schema"], "HOLE_PAIR_FUTURE_ACTIONS_BATCH_V1")
            link = root / "link.json"
            link.symlink_to(original)
            with self.assertRaisesRegex(ValueError, "untrusted_input_file"):
                g._load_file(link)
            with self.assertRaisesRegex(ValueError, "untrusted_input_file"):
                g._load_file(original, max_bytes=2)


if __name__ == "__main__":
    unittest.main()
