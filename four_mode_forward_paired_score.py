"""Result-last four-mode forward comparison. Read-only and NEVER formal evidence."""
import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

from collect_clean_results import BASE as CONFIRMED_RESULT_SOURCE_BASE

PROTOCOL = Path(__file__).resolve().parent / "research/four_mode_all_modes_forward_protocol_20261106.json"
COUNTS = {"narrow": 5, "hit": 10, "balance": 16, "hole": 22}
TOPS = (1, 3, 5, 10)
CODE = re.compile(r"20\d{6}(?:0[1-9]|1\d|2[0-4])(?:0[1-9]|1[0-2])\Z")
COMBO = re.compile(r"[1-6]-[1-6]-[1-6]\Z")
SHA = re.compile(r"[0-9a-f]{64}\Z")
PROTOCOL_SHA256 = "ed94706b9b9bb3194f5e89e358c23df46b1f704b5d84cdf44bc9a225b24b91ff"


def clock(value):
    try:
        d = datetime.fromisoformat(value)
    except (TypeError, ValueError) as e:
        raise ValueError("invalid_clock") from e
    if d.utcoffset() != timedelta(hours=9):
        raise ValueError("non_JST_clock")
    return d


def protocol_check(p):
    if type(p) is not dict:
        raise ValueError("invalid_protocol")
    canonical = json.dumps(p, sort_keys=True, separators=(",", ":")).encode()
    if hashlib.sha256(canonical).hexdigest() != PROTOCOL_SHA256:
        raise ValueError("changed_forward_protocol")
    return p


def validate_tickets(v, size):
    if not isinstance(v, list) or len(v) != size or len(set(map(str, v))) != size or any(
        not isinstance(t, str) or not COMBO.fullmatch(t) or len(set(t.split("-"))) != 3 for t in v
    ):
        raise ValueError("invalid_or_changed_ticket_budget")
    return v


def freeze(row, p):
    if not isinstance(row, dict) or any(k in row for k in
       ("result", "finish_order", "winning_ticket", "confirmed_at_jst", "payout")):
        raise ValueError("outcome_leak_in_pre_result_roster")
    code = row.get("race_code")
    if not isinstance(code, str) or not CODE.fullmatch(code):
        raise ValueError("invalid_race_code")
    deadline = clock(row.get("deadline_jst"))
    if (not clock(p["eligible_deadline_start_jst"]) <= deadline <= clock(p["eligible_deadline_end_jst"])
        or deadline.strftime("%Y%m%d") != code[:8] or row.get("model_version") != p["model_version"]):
        raise ValueError("date_or_model_version_mismatch")
    cutoff = deadline - timedelta(minutes=12)
    try:
        source = clock(row["official_source_received_jst"])
        bg = clock(row["baseline_generated_jst"])
        bo = clock(row["baseline_github_observed_jst"])
        cg = clock(row["candidate_generated_jst"])
        co = clock(row["candidate_github_observed_jst"])
    except KeyError as e:
        raise ValueError("missing_clock") from e
    # The original must be remotely observable BEFORE the candidate is
    # generated. GitHub's Date header has one-second resolution, so require
    # a full-second gap around both original and candidate observations.
    if not (source < bg and
            bg + timedelta(seconds=1) < bo and
            bo + timedelta(seconds=1) < cg and
            cg + timedelta(seconds=1) < co < cutoff):
        raise ValueError("late_or_same_second_T12")
    if (row.get("official_beforeinfo_complete_6") is not True or
        row.get("official_exhibition_complete_6") is not True or
        row.get("official_odds_complete_120") is not True or
        row.get("result_based_features_used") is not False):
        raise ValueError("incomplete_or_postrace_feature")
    if any(not isinstance(row.get(key), str) or not SHA.fullmatch(row[key]) for key in
           ("source_sha256", "original_forecast_sha256", "candidate_method_sha256")):
        raise ValueError("unanchored_source_or_method")
    selectors = row.get("mode_candidate_selector_sha256")
    if not isinstance(selectors, dict) or set(selectors) != set(COUNTS) or any(
        not isinstance(v, str) or not SHA.fullmatch(v) for v in selectors.values()
    ):
        raise ValueError("missing_four_mode_selectors")
    for kind in ("baseline", "candidate"):
        if not isinstance(row.get(kind), dict) or set(row[kind]) != set(COUNTS):
            raise ValueError("missing_four_modes")
        for mode,size in COUNTS.items():
            validate_tickets(row[kind][mode], size)
    if row.get("formal") is True or row.get("model_improvement_proven") is True:
        raise ValueError("forged_formal_status")
    return {"code": code, "deadline": deadline, "baseline": row["baseline"],
            "candidate": row["candidate"], "selectors": tuple(sorted(selectors.items())),
            "method": row["candidate_method_sha256"]}


def score(pre_result_rows, results, p):
    protocol_check(p)
    if not isinstance(pre_result_rows,list) or not isinstance(results,dict):
        raise ValueError("invalid_inputs")
    roster = {}
    excluded = Counter()
    for item in pre_result_rows:
        try:
            row = freeze(item,p)
        except (ValueError,KeyError,TypeError) as e:
            excluded[str(e)] += 1
            continue
        if row["code"] in roster:
            raise ValueError("duplicate_candidate")
        roster[row["code"]] = row
    # Do not silently replace a rejected pre-result candidate with a later race
    # to fill the fixed 300+300 cohort. An incomplete mixed roster is unscorable.
    if excluded and roster:
        raise ValueError("incomplete_candidate_roster_no_replacement")
    # All selector and method bytes must be fixed BEFORE any result lookup.
    if len({(r["selectors"],r["method"]) for r in roster.values()}) > 1:
        raise ValueError("selector_changed_across_future_races")
    ordered = sorted(roster.values(),key=lambda r:(r["deadline"],r["code"]))[:600]
    scores = {phase:{m:{f"top{k}":{"baseline":0,"candidate":0,"gained":0,"lost":0}
                   for k in TOPS} for m in COUNTS} for phase in ("pilot","confirmation")}
    # This scorer is NEVER a formal certifier. Report phase progress separately
    # from the official 300+300 study to avoid promoting replayed evidence.
    # A pending/invalid outcome reserves its pre-result roster slot.
    phase_slots = {
        "pilot": len(ordered[:p["pilot_races"]]),
        "confirmation": len(ordered[p["pilot_races"]:p["pilot_races"] + p["confirmation_races"]]),
    }
    pending_by_phase = Counter()
    invalid_by_phase = Counter()
    matched = Counter(); pending = []; bad = Counter()
    for index,row in enumerate(ordered):
        code = row["code"]
        phase = "pilot" if index < p["pilot_races"] else "confirmation"
        if code not in results or results[code] is None:
            pending.append(code)
            pending_by_phase[phase] += 1
            continue
        outcome = results[code]
        try:
            expected_result_url = (CONFIRMED_RESULT_SOURCE_BASE + code[:4] + "/"
                                   + code[4:6] + "/" + code[6:8] + ".csv")
            if not isinstance(outcome,dict):
                raise ValueError("untrusted_result_or_time")
            confirmed = clock(outcome.get("confirmed_at_jst"))
            collected = clock(outcome.get("collected_at_jst"))
            if (outcome.get("race_code") != code or
                outcome.get("status") != "confirmed" or
                outcome.get("source_url") != expected_result_url or
                not isinstance(outcome.get("source_sha256"),str) or
                not SHA.fullmatch(outcome["source_sha256"]) or
                confirmed <= row["deadline"] or
                collected < confirmed):
                raise ValueError("untrusted_result_or_time")
            finish = outcome.get("finish_order")
            if (type(finish) is not list or len(finish) != 3 or
                any(type(x) is not int or not 1<=x<=6 for x in finish) or len(set(finish)) != 3):
                raise ValueError("invalid_finish")
        except (ValueError,KeyError,TypeError) as e:
            bad[str(e)] += 1
            invalid_by_phase[phase] += 1
            continue
        matched[phase] += 1
        winning = "-".join(map(str,finish))
        for mode in COUNTS:
            for k in TOPS:
                a = winning in row["baseline"][mode][:k]
                b = winning in row["candidate"][mode][:k]
                c = scores[phase][mode][f"top{k}"]
                c["baseline"] += int(a); c["candidate"] += int(b)
                c["gained"] += int(b and not a); c["lost"] += int(a and not b)
    for phase in scores:
        for mode in scores[phase]:
            for k in TOPS:
                c = scores[phase][mode][f"top{k}"]
                c["denominator_reference_only"] = matched[phase]
                if c["candidate"]-c["baseline"] != c["gained"]-c["lost"]:
                    raise ValueError("paired_score_mismatch")
    phase_progress = {}
    for phase, target in (("pilot", p["pilot_races"]),
                          ("confirmation", p["confirmation_races"])):
        reserved = phase_slots[phase]
        confirmed = matched[phase]
        waiting = pending_by_phase[phase]
        invalid = invalid_by_phase[phase]
        if reserved != confirmed + waiting + invalid:
            raise ValueError("phase_roster_result_partition_mismatch")
        phase_progress[phase] = {
            "target": target,
            "reserved_pre_result_slots_reference_only": reserved,
            "unreserved_slots": target - reserved,
            "matched_result_pairs_reference_only": confirmed,
            "pending_result_slots": waiting,
            "invalid_result_slots": invalid,
            "reference_status": (
                "not_started" if reserved == 0 else
                "reference_complete_nonformal" if reserved == target and
                confirmed == target else "collecting_reference_only"),
            "formal_status": "not_started_unverified_first_receipt_and_official_T12",
            "formally_certified_pairs": 0,
        }
    return {"status":"reference_only_not_certified", "formal":False,
            "model_improvement_proven":False, "model_promotion_allowed":False,
            "independent_first_remote_receipt_verified":False,
            "complete_capture_run_inventory_verified":False,
            "eligible_roster_count":len(ordered), "matched_by_phase":dict(matched),
            "phase_progress":phase_progress,
            "pending_result_codes":pending,"invalid_result_counts":dict(bad),
            "excluded_before_result_read":dict(excluded),"scores":scores,
            "warning":"GitHub observation != first remote receipt. This script cannot authenticate supplied SHA or timestamps. No formal/prospective performance without independent source bytes and complete capture-run inventory."}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pre-result-roster",type=Path)
    ap.add_argument("--results",type=Path)
    args=ap.parse_args()
    p=protocol_check(json.loads(PROTOCOL.read_text(encoding="utf-8")))
    if args.pre_result_roster is None or args.results is None:
        print(json.dumps({"status":"protocol_valid_no_future_records_scored", "formal":False,
                          "model_improvement_proven":False,"model_promotion_allowed":False}))
        return
    print(json.dumps(score(json.loads(args.pre_result_roster.read_text(encoding="utf-8")),
                           json.loads(args.results.read_text(encoding="utf-8")),p),ensure_ascii=False,sort_keys=True))


if __name__ == "__main__":
    main()
