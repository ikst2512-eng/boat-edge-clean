"""Pure, outcome-blind enrollment of a predeclared fixed 300-race research cohort.

Caller must supply authentic first-add, same-job shadow and server-Date records
that passed forward_hole_saved_evidence_gate.inspect_race(score_outcome=False).
This module cannot authenticate those origins or assert exhaustive Actions
inventory. NEVER pick the first 300 races with known winning results.
"""
import hashlib
import json
import re
from datetime import datetime, timedelta
from forward_hole_rank3_protocol import validate as validate_protocol

CODES = re.compile(r"20[0-9]{6}(?:0[1-9]|1[0-9]|2[0-4])(?:0[1-9]|1[0-2])\Z")
SHA = re.compile(r"[a-f0-9]{40}\Z")
HEX = re.compile(r"[a-f0-9]{64}\Z")
TICKET = re.compile(r"[1-6]-[1-6]-[1-6]\Z")
TOP = 300
JST = timedelta(hours=9)
UTC = timedelta(0)
EXPECTED_KEYS = {
    "race_code", "status", "deadline_jst", "source_git_commit_sha",
    "source_sha256", "github_server_observed_at_utc", "baseline_top10",
    "candidate_top10", "formal", "first_remote_receipt_verified",
    "capture_run_inventory_verified", "original_actions_artifact_origin_authenticated",
    "result_accessed", "warning",
}


def _date(value, offset):
    if type(value) is not str:
        raise ValueError("missing_datetime")
    try:
        date = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("invalid_datetime") from exc
    if date.utcoffset() != offset:
        raise ValueError("unexpected_timezone")
    return date


def _tickets(values):
    if (type(values) is not list or len(values) != 10
            or any(type(t) is not str or TICKET.fullmatch(t) is None
                   or len(set(t.split("-"))) != 3 for t in values)
            or len(set(values)) != 10):
        raise ValueError("invalid_enrollment_ticket_list")
    return values


def _receipt(receipt, valid_protocol):
    if (type(receipt) is not dict
            or receipt.get("status") != "research_protocol_on_github_before_study_cutoff"
            or receipt.get("schema") != "FOUR_MODE_RESEARCH_PROTOCOL_GITHUB_SERVER_OBSERVATION_V1"
            or receipt.get("protocol_file") != "research/forward_hole_rank3_protocol_20261105.json"
            or receipt.get("protocol_sha256") != valid_protocol["protocol_sha256"]
            or type(receipt.get("protocol_commit_sha")) is not str
            or SHA.fullmatch(receipt["protocol_commit_sha"]) is None
            or receipt.get("server_response_not_first_receipt_proof") is not True
            or receipt.get("observed_protocol_only_not_forecasts") is not True
            or receipt.get("formal") is not False
            or receipt.get("remote_forecasts_verified") is not False
            or receipt.get("eligible_races_proven") is not False
            or receipt.get("production_promotion_allowed") is not False):
        raise ValueError("protocol_receipt_untrusted")
    observed = _date(receipt.get("github_server_date_utc"), UTC)
    cutoff = _date(receipt.get("predeclared_observation_deadline_jst"), JST)
    if cutoff.isoformat() != "2026-11-05T07:00:00+09:00" or observed >= cutoff:
        raise ValueError("protocol_observation_not_pre_study")
    return observed


def _read_pre_result(row):
    if type(row) is not dict or set(row) != EXPECTED_KEYS:
        raise ValueError("unexpected_pre_result_fields")
    code = row.get("race_code")
    if type(code) is not str or CODES.fullmatch(code) is None:
        raise ValueError("invalid_race_id")
    if not "20261105" <= code[:8] <= "20261231":
        raise ValueError("outside_predeclared_period")
    if (row.get("status") != "pre_result_evidence_consistent_research_only"
            or row.get("result_accessed") is not False
            or row.get("formal") is not False
            or row.get("first_remote_receipt_verified") is not False
            or row.get("capture_run_inventory_verified") is not False
            or row.get("original_actions_artifact_origin_authenticated") is not False):
        raise ValueError("pre_result_gate_not_passed")
    sha = row.get("source_git_commit_sha")
    digest = row.get("source_sha256")
    if (type(sha) is not str or SHA.fullmatch(sha) is None
            or type(digest) is not str or HEX.fullmatch(digest) is None):
        raise ValueError("original_ref_invalid")
    deadline = _date(row.get("deadline_jst"), JST)
    observed = _date(row.get("github_server_observed_at_utc"), UTC)
    if deadline.strftime("%Y%m%d") != code[:8] or not observed < deadline - timedelta(minutes=12):
        raise ValueError("post_cutoff_or_wrong_race")
    base = _tickets(row.get("baseline_top10"))
    candidate = _tickets(row.get("candidate_top10"))
    if (base[:2] != candidate[:2]
            or not {tuple(t.split("-")[:2]) for t in base}.issubset(
                {tuple(t.split("-")[:2]) for t in candidate})):
        raise ValueError("changed_predeclared_budget_or_pair_coverage")
    return {
        "race_code": code,
        "deadline_jst": deadline.isoformat(),
        "source_git_commit_sha": sha,
        "source_sha256": digest,
        "github_server_observed_at_utc": observed.isoformat(),
        "baseline_top10": base,
        "candidate_top10": candidate,
    }


def build_pre_result_membership(pre_result_rows, protocol_remote_receipt, *,
                                capture_inventory_verified=False):
    """Outcome data is forbidden; all metrics withheld even for 300 rows.

    capture_inventory_verified is metadata from a separate audit (not proved
    here). The returned membership is provisional regardless of this flag.
    """
    protocol = validate_protocol()
    _receipt(protocol_remote_receipt, protocol)
    if type(pre_result_rows) is not list or type(capture_inventory_verified) is not bool:
        raise ValueError("invalid_enrollment_input")
    if len(pre_result_rows) > 20000:
        raise ValueError("unbounded_enrollment_inventory")
    pre = [_read_pre_result(row) for row in pre_result_rows]
    unique = {x["race_code"] for x in pre}
    if len(unique) != len(pre):
        raise ValueError("duplicate_original_race")
    ordered = sorted(pre, key=lambda x: (x["deadline_jst"], x["race_code"]))
    # Deadline strings all have +09:00 and parsed ISO formats; same-clock
    # string ordering can differ if seconds are omitted. Always compare real
    # aware dates, and break any exact deadline tie by race ID.
    ordered = sorted(pre, key=lambda x: (
        _date(x["deadline_jst"], JST), x["race_code"]))
    chosen = ordered[:TOP]
    roster = [x["race_code"] for x in chosen]
    membership_bytes = json.dumps(
        [{"race_code": x["race_code"], "source_sha256": x["source_sha256"],
          "baseline_top10": x["baseline_top10"],
          "candidate_top10": x["candidate_top10"]} for x in chosen],
        ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode("ascii")
    status = ("provisional_first_300_pre_result_members_identified"
              if len(chosen) == TOP else "awaiting_300_pre_result_members")
    return {
        "schema": "HOLE_PRE_RESULT_FIRST300_MEMBERSHIP_RESEARCH_V1",
        "status": status,
        "required_members": TOP,
        "observed_pre_result_candidates": len(pre),
        "enrolled_members": len(chosen),
        "over_cap_non_enrolled": max(0, len(pre) - TOP),
        "membership_order": "deadline_jst_ascending_then_race_code_ascending",
        "roster_codes": roster,
        "roster_sha256": hashlib.sha256(
            ("\n".join(roster) + "\n").encode("ascii")).hexdigest(),
        "exact_frozen_ticket_membership_sha256": hashlib.sha256(membership_bytes).hexdigest(),
        "frozen_pre_result_member_records": chosen,
        "protocol_sha256": protocol["protocol_sha256"],
        "evidence_origin_independently_authenticated": False,
        "complete_capture_run_inventory_verified_here": False,
        "caller_claimed_inventory_verified": capture_inventory_verified,
        "roster_committed_before_any_result": False,
        "no_outcome_consulted": True,
        "pending_results_still_occupy_their_slots": True,
        "formal": False,
        "efficacy_p_value": None,
        "model_improvement_proven": False,
        "production_promotion_allowed": False,
        "warning": ("Provisional arithmetic-only cohort. A qualified remote first-seen "
                    "and complete independent Actions inventory are still missing; "
                    "persist this roster before opening ANY result; missing results "
                    "must never be replaced by later enrolled candidates."),
    }
