"""Research-only #1694 same-race T-12 report -> #1698 blocker bridge.

DOES NOT reimplement #1694 source collection or authentication.
Consumes a caller-supplied independently generated report; verifies its
internal structural consistency, not authorship. NO official readiness
or formal candidate certification can be granted from a JSON alone.
"""
from collections import Counter
import re

SCHEMA = "POSITION_SENSITIVE_CROSS_PR_T12_BLOCKER_BRIDGE_V1"
UPSTREAM = "T12_SAME_RACE_INDEPENDENT_PROOF_CHAIN_V1"
CODE = re.compile(r"20[0-9]{10}\Z")
COMPONENTS = (
    "official_racelist_original",
    "official_beforeinfo_original",
    "official_odds_original",
    "six_boat_exhibition_complete",
    "official_t12_source_cutoff_met",
    "independent_source_archive_server_publication_by_t12",
    "frozen_forecast_generated_after_all_originals",
    "actual_model_input_consumption_verified",
    "independent_first_forecast_git_remote_receipt_verified",
    "final_race_entry_verified",
)
SCORING = ("same_race_three_source_readiness", "formal")


def _code(value):
    if (type(value) is not str or not CODE.fullmatch(value)
            or not 1 <= int(value[8:10]) <= 24
            or not 1 <= int(value[10:12]) <= 12):
        raise ValueError("invalid_race_code")
    return value


def assess_cross_pr_blockers(source_report, candidate_race_codes):
    """Never scores races, never grants eligibility, never fills missing sources.

    The candidate roster is informational ONLY; self-supplied race IDs are not
    authenticated first-add / remote-first-seen receipts.
    """
    if type(source_report) is not dict or type(candidate_race_codes) not in (list, tuple):
        raise ValueError("invalid_inputs")
    if (source_report.get("schema") != UPSTREAM
            or source_report.get("cross_race_original_combination_allowed") is not False
            or source_report.get("formal") is not False
            or source_report.get("t12_eligible") is not False
            or source_report.get("accuracy_scoring_allowed") is not False
            or source_report.get("new_formal_certifications") != 0
            or source_report.get("formal_accuracy_denominator") is not None):
        raise ValueError("upstream_report_overclaims_or_schema_unknown")
    source_races = source_report.get("races")
    if type(source_races) is not list or type(source_report.get("races_compared")) is not int:
        raise ValueError("invalid_source_race_census")
    if len(source_races) != source_report["races_compared"]:
        raise ValueError("source_race_count_mismatch")
    ids = [_code(x) for x in candidate_race_codes]
    if len(set(ids)) != len(ids):
        raise ValueError("candidate_roster_duplicate")
    if len(ids) > 600:
        raise ValueError("candidate_roster_exceeds_protocol_limit")

    source_by_code = {}
    for row in source_races:
        if type(row) is not dict:
            raise ValueError("invalid_upstream_race_row")
        code = _code(row.get("race_code"))
        if code in source_by_code or row.get("day_jst") != code[:8]:
            raise ValueError("duplicate_or_cross_day_source_row")
        if any(type(row.get(key)) is not bool for key in COMPONENTS + SCORING):
            raise ValueError("missing_untyped_source_component")
        missing = row.get("missing_requirements")
        if (type(missing) is not list or not missing
                or any(type(x) is not str or not x or len(x) > 160 for x in missing)
                or len(set(missing)) != len(missing)):
            raise ValueError("missing_source_blocker_or_duplicate")
        if row["formal"] is not False:
            raise ValueError("unexpected_upstream_formal_race")
        # Never let a historical nonformal upstream report claim a complete
        # certification via duplicated/truthy booleans or stitched components.
        triad = all(row[k] for k in (
            "official_racelist_original", "official_beforeinfo_original",
            "official_odds_original", "six_boat_exhibition_complete",
            "official_t12_source_cutoff_met"))
        if row["same_race_three_source_readiness"] != triad:
            raise ValueError("triad_completeness_disagrees_with_components")
        source_by_code[code] = row

    if (source_report.get("fully_qualified_same_race_three_original_t12_sources") !=
            sum(x["same_race_three_source_readiness"] for x in source_races)
            or source_report.get("forecasts_generated_after_all_originals") !=
            sum(x["frozen_forecast_generated_after_all_originals"] for x in source_races)):
        raise ValueError("upstream_aggregate_component_disagreement")

    examined = []
    why = Counter()
    for code in ids:
        row = source_by_code.get(code)
        if row is None:
            blockers = ["no_same_race_upstream_source_report"]
            reasons = []
            availability = {k: "unknown_no_upstream_row" for k in COMPONENTS}
        else:
            availability = {
                key: ("self_reported_present_not_reauthenticated" if row[key]
                      else "reported_missing_or_unverified")
                for key in COMPONENTS}
            blockers = [k for k in COMPONENTS if not row[k]]
            reasons = list(row["missing_requirements"])
            if not blockers:
                # Even a complete row is only a caller-supplied report.
                blockers = ["upstream_authenticity_and_candidate_receipts_not_verified_here"]
        for blocker in blockers:
            why[blocker] += 1
        examined.append({
            "race_code": code,
            "same_race_report_matched": row is not None,
            "upstream_component_readiness_claims": availability,
            "blockers": blockers,
            "upstream_missing_reasons_non_authoritative": reasons,
            "official_provenance_independently_reaudited_by_this_bridge": False,
            "eligible_for_300_plus_300": False,
        })
    return {
        "schema": SCHEMA,
        "status": "historical_same_race_blocker_alignment_only",
        "input_candidate_codes": len(ids),
        "matched_upstream_race_codes": sum(x["same_race_report_matched"] for x in examined),
        "unmatched_candidate_codes": sum(not x["same_race_report_matched"] for x in examined),
        "by_race": examined,
        "blocker_counts_non_exclusive": dict(sorted(why.items())),
        "historical_upstream_report_self_authenticated": False,
        "actual_source_original_bytes_read_by_this_bridge": False,
        "candidate_remote_first_receipt_independently_verified": False,
        "complete_forward_capture_roster_verified": False,
        "new_formal_pilot_slots": 0,
        "new_formal_confirmation_slots": 0,
        "outcomes_read": False,
        "formal": False,
        "model_improvement_proven": False,
        "promotion_allowed": False,
        "production_changed": False,
        "warning": (
            "Cross-PR upstream JSON and candidate code lists alone cannot "
            "authenticate official content, real first remote candidate "
            "receipt, model input consumption or formal prospective cohorts. "
            "No cross-race original substitution, outcome read or scoring."
        ),
    }



def _reject_duplicate_keys(pairs):
    data = {}
    for key, value in pairs:
        if key in data:
            raise ValueError("duplicate_json_key")
        data[key] = value
    return data


def _read_json_file(path, maximum):
    """Treat both upstream reports and candidate rosters as UNTRUSTED files."""
    from pathlib import Path
    import json
    path = Path(path)
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= maximum:
        raise ValueError("unsafe_json_report_path")
    return json.loads(path.read_bytes(), object_pairs_hook=_reject_duplicate_keys)


def main():
    """Offline manual handoff only; prints noncertifying blocker JSON to stdout."""
    import argparse
    import json

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--t12-report", required=True)
    parser.add_argument("--candidate-codes", required=True)
    args = parser.parse_args()
    source = _read_json_file(args.t12_report, 250_000)
    codes = _read_json_file(args.candidate_codes, 30_000)
    print(json.dumps(assess_cross_pr_blockers(source, codes),
                     ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
