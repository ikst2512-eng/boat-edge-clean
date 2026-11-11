"""Future official-source candidate *lineage preflight* (nonformal).

An independent official-source re-auditor must still parse each real original,
establish racer/exhibition/odds authenticity and attest first remote receipt.
This module is an intentionally narrower, result-blind byte/clock/lineage gate:
it will NEVER certify official source authenticity, model consumption,
first remote receipt or prospective predictive improvement.

It does not change the frozen four-mode selector or registered 300+300 study,
fetch sources, run predictions, write forecast data, or read race results.
"""
import argparse
import base64
import binascii
import hashlib
import json
import math
import re
from datetime import datetime, timedelta
from itertools import permutations
from pathlib import Path

SCHEMA = "FOUR_MODE_FUTURE_OFFICIAL_INPUT_LINEAGE_PREFLIGHT_V1"
KINDS = ("racelist", "beforeinfo", "odds120")
SIZES = {"narrow": 5, "hit": 10, "balance": 16, "hole": 22}
CODE = re.compile(r"20[0-9]{10}\Z")
HASH = re.compile(r"[0-9a-f]{64}\Z")
COMBOS = {"-".join(p) for p in permutations("123456", 3)}
BLOCKED = {"finish_order", "winning_ticket", "confirmed_result", "result",
           "confirmed_at_jst", "payout", "winning_combo",
           "post_race_weather", "post_race_entry", "final_entry_course",
           "official_result"}


def has_embedded_outcome(data):
    """Inspect JSON-like metadata recursively, including otherwise unused fields.

    A hidden result under auxiliary metadata is still post-result leakage;
    top-level-only checks cannot safely accept the purported pre-result input.
    An input containing cycles is never produced by JSON, but is bounded here
    for direct Python callers rather than allowing endless recursion.
    """
    pending = [data]
    visited = set()
    while pending:
        node = pending.pop()
        if type(node) not in (dict, list, tuple):
            continue
        identity = id(node)
        if identity in visited:
            continue
        visited.add(identity)
        if len(visited) > 100_000:
            raise ValueError("oversized_nested_pre_result_input")
        if type(node) is dict:
            if any(key in BLOCKED for key in node):
                return True
            pending.extend(node.values())
        else:
            pending.extend(node)
    return False


def _jst(value):
    try:
        when = datetime.fromisoformat(value)
    except (ValueError, TypeError) as exc:
        raise ValueError("invalid_jst_clock") from exc
    if when.utcoffset() != timedelta(hours=9):
        raise ValueError("non_jst_clock")
    return when


def _canonical(v):
    return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def preflight(source_bundle, candidate):
    """Verify raw BYTE matching, strict chronology and declared consumption.

    All source/normalization/candidate inputs are caller-supplied and are NOT
    independently authenticated. Even a structurally valid report is nonformal.
    """
    if (type(source_bundle) is not dict or type(candidate) is not dict or
            source_bundle.get("schema") != SCHEMA):
        raise ValueError("invalid_lineage_schema")
    # Preserve the sharper normalized-source diagnostic while examining
    # *all* other metadata recursively for hidden postrace information.
    if has_embedded_outcome(source_bundle.get("normalized_source_claim")):
        raise ValueError("outcome_leak_in_normalized_claim")
    if (has_embedded_outcome(source_bundle) or has_embedded_outcome(candidate)
            or source_bundle.get("formal") is True or candidate.get("formal") is True):
        raise ValueError("outcome_or_forged_formal_in_pre_result_input")
    code = source_bundle.get("race_code")
    if (type(code) is not str or not CODE.fullmatch(code)
            or candidate.get("race_code") != code):
        raise ValueError("cross_race_candidate_identity")
    cutoff = _jst(source_bundle.get("deadline_jst")) - timedelta(minutes=12)
    if (cutoff + timedelta(minutes=12)).strftime("%Y%m%d") != code[:8]:
        raise ValueError("deadline_day_does_not_match_race")
    if candidate.get("deadline_jst") != source_bundle["deadline_jst"]:
        raise ValueError("candidate_deadline_mismatch")
    originals = source_bundle.get("originals")
    normalized = source_bundle.get("normalized_source_claim")
    if type(originals) is not dict or set(originals) != set(KINDS):
        raise ValueError("missing_or_extra_official_original")
    if type(normalized) is not dict or normalized.get("race_code") != code:
        raise ValueError("missing_normalized_claim_or_race")
    if has_embedded_outcome(normalized):
        raise ValueError("outcome_leak_in_normalized_claim")
    raw_digests = {}
    source_times = []
    for kind in KINDS:
        record = originals[kind]
        if (type(record) is not dict or
                type(record.get("raw_base64")) is not str or
                type(record.get("sha256")) is not str or
                HASH.fullmatch(record["sha256"]) is None or
                type(record.get("source_url")) is not str or
                not record["source_url"].startswith("https://www.boatrace.jp/")):
            raise ValueError("missing_original_raw_bytes_or_source_identity")
        try:
            raw = base64.b64decode(record["raw_base64"], validate=True)
        except (ValueError, binascii.Error) as exc:
            raise ValueError("invalid_original_base64") from exc
        if (not 0 < len(raw) <= 1_000_000 or
                hashlib.sha256(raw).hexdigest() != record["sha256"]):
            raise ValueError("original_byte_hash_mismatch")
        received = _jst(record.get("received_at_jst"))
        if received.strftime("%Y%m%d") != code[:8]:
            raise ValueError("cross_day_source_receipt")
        if not received < cutoff:
            raise ValueError("original_received_after_T_minus_12")
        raw_digests[kind] = record["sha256"]
        source_times.append(received)
    if normalized.get("source_sha256") != raw_digests:
        raise ValueError("normalized_claim_not_bound_to_raw_bytes")
    # These are STRUCTURAL checks on an explicitly untrusted normalization,
    # NOT proof that the source originals actually parse to these values.
    ids = normalized.get("racelist_registration_ids")
    before_ids = normalized.get("beforeinfo_registration_ids")
    if (type(ids) is not list or type(before_ids) is not list or
            len(ids) != 6 or len(set(ids)) != 6 or ids != before_ids or
            any(type(v) is not str or not re.fullmatch(r"[0-9]{4,6}", v)
                for v in ids)):
        raise ValueError("racer_identity_six_mismatch")
    course = normalized.get("exhibition_courses")
    times = normalized.get("exhibition_times")
    st = normalized.get("exhibition_st")
    tilts = normalized.get("exhibition_tilts")
    if (type(course) is not list or sorted(course) != [1,2,3,4,5,6]
            or any(type(x) is not int for x in course)
            or type(times) is not list or len(times) != 6
            or type(st) is not list or len(st) != 6
            or type(tilts) is not list or len(tilts) != 6
            or any(type(v) not in (float,int) or not math.isfinite(v)
                   or not -5 <= v <= 5 for v in tilts)
            or any(type(v) not in (float,int) or not math.isfinite(v)
                   or not 0 < v < 20 for v in times)
            or any(type(v) not in (float,int) or not math.isfinite(v)
                   or not -1 < v < 2 for v in st)):
        raise ValueError("missing_or_invalid_six_exhibition_entries")
    odds = normalized.get("odds_3t")
    if (type(odds) is not dict or set(odds) != COMBOS or
            any(type(v) not in (float,int) or not math.isfinite(v)
                   or not 0 < v < 10000000 for v in odds.values())):
        raise ValueError("odds_not_exactly_120_unique_combinations")
    normalized_digest = hashlib.sha256(_canonical(normalized)).hexdigest()

    if (candidate.get("consumed_source_sha256") != raw_digests
            or candidate.get("consumed_normalized_claim_sha256") != normalized_digest):
        raise ValueError("candidate_declared_source_digests_mismatch")
    method = candidate.get("candidate_method_sha256")
    if type(method) is not str or HASH.fullmatch(method) is None:
        raise ValueError("missing_method_byte_identity")
    modes = candidate.get("candidate_tickets")
    if type(modes) is not dict or set(modes) != set(SIZES):
        raise ValueError("missing_or_unexpected_four_modes")
    for mode, size in SIZES.items():
        tickets = modes[mode]
        if type(tickets) is not list or len(tickets) != size or \
           len(set(tickets)) != size or any(x not in COMBOS for x in tickets):
            raise ValueError("candidate_ticket_budget_or_identity_invalid")
    generated = _jst(candidate.get("generated_at_jst"))
    if not max(source_times) + timedelta(seconds=1) < generated < cutoff:
        raise ValueError("source_to_candidate_time_order_not_proven")
    if (candidate.get("official_source_authenticity_verified") is True or
            candidate.get("model_input_consumption_independently_replayed") is True or
            candidate.get("independent_first_remote_receipt_verified") is True):
        raise ValueError("caller_claims_unverifiable_independent_evidence")
    return {
        "schema": SCHEMA,
        "race_code": code,
        "status": "source_bytes_and_declared_model_lineage_structurally_consistent_ONLY",
        "raw_originals_three_sha256_recalculated": True,
        "claimed_six_exhibition_entries_structurally_valid": True,
        "claimed_120_odds_structurally_valid": True,
        "declared_candidate_source_hashes_match": True,
        "source_to_candidate_self_reported_clock_order": True,
        "official_source_authenticity_independently_replayed": False,
        "actual_model_consumption_independently_replayed": False,
        "candidate_method_preregistered_before_generation_verified": False,
        "independent_first_remote_candidate_receipt_verified": False,
        "complete_run_attempt_inventory_verified": False,
        "formal": False, "prospective_candidate_admitted": False,
        "formal_count": 0, "model_improvement_proven": False,
        "model_promotion_allowed": False,
        "warning": "Source URL, source receive clocks, parsed fields, model behavior "
                   "and first remote receipt are not authenticated by this local "
                   "preflight. No production or cohort admission is authorized.",
    }



def _load_local_json(value):
    path = Path(value)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 5_000_000:
        raise ValueError("invalid_or_oversized_local_input")
    return json.loads(path.read_bytes())


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-bundle", required=True,
                   help="Separate, untrusted official-source original-byte manifest")
    p.add_argument("--candidate", required=True,
                   help="Future candidate's declared source-byte lineage")
    p.add_argument("--output", type=Path,
                   help="Optional RESEARCH report only; never a forecast")
    a = p.parse_args()
    result = preflight(_load_local_json(a.source_bundle),
                       _load_local_json(a.candidate))
    payload = json.dumps(result, sort_keys=True, ensure_ascii=False, indent=2)+"\n"
    if a.output:
        if a.output.is_symlink():
            raise ValueError("refuse_report_symlink")
        a.output.write_text(payload, encoding="utf-8")
    print("FUTURE_OFFICIAL_LINEAGE_NONFORMAL=" +
          json.dumps(result, sort_keys=True, ensure_ascii=False))


if __name__ == "__main__":
    main()
