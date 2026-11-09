"""Read-only, nonformal prospective hole-pair evidence gap ledger.

Use a complete immutable-main *candidate* snapshot manifest and optional
self-reported D1 receipts / external-audit report pointers. Never download
sources or scores, create a freeze, claim authentic external timestamps, or
count formal pilot/confirmation entries. Official source verification remains
owned by the separate T-12 independent source auditor.
"""
import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from hole_pair_remote_receipt_evidence import canonical_bytes, _validate_frozen
from research.hole_pair_d1_receipt_chain_audit import audit_one
from research.hole_pair_universe_coverage import reconcile

SHA64 = re.compile(r"[0-9a-f]{64}\Z")
LABEL = re.compile(r"[A-Za-z0-9_./:#-]{1,180}\Z")
SCHEMA = "HOLE_PAIR_PROSPECTIVE_EVIDENCE_GAP_LEDGER_V1"
FIXED_BLOCKERS = (
    "independent_first_candidate_server_acceptance_unverified",
    "official_deadline_and_t12_authentication_unverified",
    "same_race_racelist_original_unverified",
    "same_race_six_boat_beforeinfo_exhibition_unverified",
    "same_race_full_120_way_odds_unverified",
    "source_received_then_prediction_generated_before_t12_unverified",
    "original_source_consumption_by_model_unverified",
    "independent_cross_run_first_write_and_conflict_audit_unverified",
    "whole_day_official_schedule_coverage_unverified",
    "independent_result_and_entry_not_checked",
)


def _source_pointer(pointer, code):
    """A report *reference* is not proof its bytes or author were verified."""
    if type(pointer) is not dict or set(pointer) != {
        "race_code", "upstream_report_sha256_claim",
        "upstream_report_locator_claim",
    }:
        raise ValueError("untrusted_source_report_pointer_schema")
    if (pointer["race_code"] != code
            or type(pointer["upstream_report_sha256_claim"]) is not str
            or SHA64.fullmatch(pointer["upstream_report_sha256_claim"]) is None
            or type(pointer["upstream_report_locator_claim"]) is not str
            or LABEL.fullmatch(pointer["upstream_report_locator_claim"]) is None):
        raise ValueError("source_report_pointer_cross_race_or_invalid")
    return {
        "upstream_report_sha256_claim": pointer["upstream_report_sha256_claim"],
        "upstream_report_locator_claim": pointer["upstream_report_locator_claim"],
        "external_report_bytes_and_authorship_independently_verified": False,
        "official_t12_complete_verified": False,
    }


def audit(manifest, d1_receipts=None, source_report_pointers=None):
    """Produce stable per-race blockers without counting any formal accuracy."""
    receipts = {} if d1_receipts is None else d1_receipts
    pointers = {} if source_report_pointers is None else source_report_pointers
    if (type(manifest) is not dict or type(receipts) is not dict
            or type(pointers) is not dict):
        raise ValueError("untrusted_gap_ledger_input")
    if (manifest.get("schema") != "HOLE_PAIR_FUTURE_ACTIONS_BATCH_V1"
            or manifest.get("status") != "local_predeadline_freeze_not_formal"
            or any(manifest.get(field) is not False for field in (
                "formal", "prospective_validation", "independent_first_receipt_verified",
                "production_forecast_changed"))):
        raise ValueError("untrusted_nonformal_manifest")
    day, main = manifest.get("capture_day_jst"), manifest.get("source_main_commit")
    codes = manifest.get("source_forecast_codes")
    records = manifest.get("records")
    excluded = manifest.get("excluded_race_codes_by_reason")
    coverage = reconcile(day, main, codes, records, excluded)
    if (manifest.get("source_snapshot_coverage") != coverage
            or manifest.get("eligible_forecasts_examined") != len(codes)
            or manifest.get("frozen_count") != len(records)
            or manifest.get("excluded_by_reason") != coverage["excluded_by_reason"]):
        raise ValueError("original_manifest_census_does_not_match")
    frozen = {}
    for record in records:
        code, _ = _validate_frozen(record)
        if code in frozen:
            raise ValueError("duplicate_candidate_in_manifest")
        frozen[code] = record
    if (any(type(code) is not str for code in receipts)
            or any(type(code) is not str for code in pointers)
            or set(receipts) - set(frozen)
            or set(pointers) - set(codes)):
        raise ValueError("orphan_d1_receipt_or_external_source_pointer")
    exclusions = {}
    for reason, group in excluded.items():
        for code in group:
            exclusions[code] = reason
    rows, counters = [], Counter()
    for code in codes:
        pointer = (_source_pointer(pointers[code], code)
                   if code in pointers else None)
        if code in exclusions:
            if pointer:
                counters["source_report_pointer_claims_for_excluded"] += 1
            rows.append({
                "race_code": code,
                "classification": "excluded_before_frozen_candidate",
                "local_exclusion_reason": exclusions[code],
                "source_report_pointer_unverified": pointer,
                "candidate_record_sha256": None,
                "d1_receipt_status": "not_applicable_no_candidate",
                "formally_eligible": False,
                "hit_miss_scoring_allowed": False,
                "exclusion_must_remain_in_universe_ledger": True,
            })
            counters["locally_excluded"] += 1
            continue
        record = frozen[code]
        audit_result = audit_one(record, receipts.get(code))
        status = audit_result["status"]
        if status not in (
            "no_receiver_receipt",
            "self_reported_d1_timestamp_consistent_not_independent_proof",
        ):
            raise ValueError("unknown_d1_audit_result_status")
        if status == "no_receiver_receipt":
            counters["candidate_d1_receipt_missing"] += 1
        else:
            counters["candidate_d1_claim_consistent_only"] += 1
        if pointer:
            counters["external_source_report_pointer_claims"] += 1
        else:
            counters["external_source_report_pointer_missing"] += 1
        blockers = list(FIXED_BLOCKERS)
        if not pointer:
            blockers.append("external_official_source_audit_report_reference_missing")
        else:
            blockers.append("external_official_source_audit_reference_unverified")
        if status == "no_receiver_receipt":
            blockers.append("d1_receiver_receipt_missing")
        else:
            blockers.append("d1_timestamp_is_self_report_not_independent_witness")
        rows.append({
            "race_code": code,
            "classification": "frozen_nonformal_prospective_candidate",
            "declared_t_minus_12_jst": record["t_minus_12_jst"],
            "local_finish_jst": record["local_finish_jst"],
            "source_main_commit": main,
            "original_source_git_blob_sha1_claim": record["source_git_blob_sha1"],
            "original_source_sha256_claim": record["source_sha256"],
            "candidate_record_sha256": audit_result["candidate_record_sha256"],
            "candidate_method_source_sha256": record["method_source_sha256"],
            "candidate_top1_top3_top5_protected_by_frozen_schema": True,
            "d1_receipt_status": status,
            "source_report_pointer_unverified": pointer,
            "missing_evidence_codes": sorted(blockers),
            "independent_first_receipt_verified": False,
            "official_t12_complete_verified": False,
            "formally_eligible": False,
            "hit_miss_scoring_allowed": False,
            "production_promotion_allowed": False,
        })
        counters["frozen_candidates_inspected"] += 1
    # The order is a census, NOT a formally admissible chronological cohort.
    return {
        "schema": SCHEMA,
        "capture_day_jst": day,
        "source_main_commit": main,
        "manifest_sha256_of_canonical_claim": hashlib.sha256(
            canonical_bytes(manifest)).hexdigest(),
        "snapshot_forecast_codes_examined": len(codes),
        "locally_excluded": counters["locally_excluded"],
        "frozen_candidates_inspected": counters["frozen_candidates_inspected"],
        "candidate_d1_receipt_missing": counters["candidate_d1_receipt_missing"],
        "candidate_d1_claim_consistent_only": counters["candidate_d1_claim_consistent_only"],
        "external_source_report_pointer_claims": counters["external_source_report_pointer_claims"],
        "external_source_report_pointer_missing": counters["external_source_report_pointer_missing"],
        "source_report_pointer_claims_for_excluded": counters["source_report_pointer_claims_for_excluded"],
        "independent_external_witness_authenticated": 0,
        "official_three_source_t12_verified": 0,
        "whole_day_schedule_verified": False,
        "prospective_pilot_formally_eligible": 0,
        "prospective_confirmation_formally_eligible": 0,
        "accuracy_denominator_authorized": False,
        "result_files_read": False,
        "formal": False,
        "production_promotion_allowed": False,
        "rows": rows,
        "warning": (
            "Report pointers and D1 JSON clocks are untrusted claims, not "
            "authenticated evidence. Exact original Git and remote first-"
            "acceptance witness, official six-boat/120-odds/T-12 and original "
            "consumption require external independent verification. Do not "
            "score, admit races, or convert a report pointer into formal proof."
        ),
    }


def _load_file(path, max_bytes=4_000_000):
    p = Path(path)
    if p.is_symlink() or not p.is_file() or p.stat().st_size > max_bytes:
        raise ValueError("untrusted_input_file")
    return json.loads(p.read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--d1-receipts", help="Optional self-reported, never signed D1 map")
    parser.add_argument("--source-report-pointers", help="Optional unverified #1694 handoff references")
    args = parser.parse_args()
    result = audit(_load_file(args.manifest),
                   _load_file(args.d1_receipts) if args.d1_receipts else None,
                   _load_file(args.source_report_pointers)
                   if args.source_report_pointers else None)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
