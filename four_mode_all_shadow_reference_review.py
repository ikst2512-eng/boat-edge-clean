"""Read-only same-race research TopN review of ALL-MODE same-job frozen shadows.

Candidate/original integrity and chronology must pass BEFORE reading any result.
No local artifact or original GitHub observation establishes FIRST REMOTE
RECEIPT of the candidate. All output is reference-only, never formal.
"""
import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

from collect_clean_results import confirmed_record_is_usable
from four_mode_all_mode_same_job_shadow import (
    SCHEMA, SIZES, VERSION, PROTECTED, TOP1_PAIR_RULE, candidate_modes,
    top1_pair_candidate, at_jst,
)

CODE = re.compile(r"20[0-9]{10}\Z")
SHA64 = re.compile(r"[0-9a-f]{64}\Z")
TOPS = (1, 3, 5, 10)
TOP1_PROTOCOL = Path(__file__).resolve().parent / "research/four_mode_top1_pair_forward_protocol_20261108.json"


def fail(reason):
    raise ValueError(reason)


def validate_capture_before_any_results(captures, root):
    """Fail closed for a partial/mixed capture; never substitute successful rows."""
    if type(captures) is not list:
        raise ValueError("invalid_capture_input")
    if not captures:
        return {}, Counter(), 0
    root = Path(root)
    method_path = Path(__file__).resolve().parent/"four_mode_all_mode_same_job_shadow.py"
    method_bytes = method_path.read_bytes()
    actual_method_sha = hashlib.sha256(method_bytes).hexdigest()
    # Independent source-blob pin, registered before any new Top1 holdout.
    # Prevent changing the candidate method while retaining self-consistent
    # replay SHA values in freshly generated artifacts.
    top1_protocol = json.loads(TOP1_PROTOCOL.read_bytes())
    git_blob_sha = hashlib.sha1(
        b"blob " + str(len(method_bytes)).encode("ascii") + b"\0" + method_bytes
    ).hexdigest()
    if (top1_protocol.get("schema") != "FOUR_MODE_TOP1_PAIR_FORWARD_PREREGISTRATION_V1"
            or top1_protocol.get("policy_id") != TOP1_PAIR_RULE
            or top1_protocol.get("pinned_selector_git_blob_sha1") != git_blob_sha
            or top1_protocol.get("promotion_allowed") is not False
            or top1_protocol.get("formal_count") != 0):
        fail("top1_selector_not_independently_preregistered")
    candidates = {}
    excluded = Counter()
    observed_total = 0
    lock = None
    for capture in captures:
        if not isinstance(capture, dict) or capture.get("schema") != SCHEMA:
            fail("capture_schema_invalid")
        if capture.get("formal") is not False or capture.get(
                "candidate_first_remote_receipt_verified") is not False:
            fail("forged_formal_or_candidate_receipt")
        if capture.get("status") not in ("original_published_candidate_research_artifact",
                                        "no_publication", "no_confirmed_publication",
                                        "no_original_remote_observation"):
            fail("unknown_capture_status")
        n = capture.get("published_count")
        frozen = capture.get("frozen_count")
        ineligible = capture.get("ineligible_count")
        errors = capture.get("validation_error_count")
        rows = capture.get("records")
        if (any(type(v) is not int or v < 0 for v in (n,frozen,ineligible,errors))
                or type(rows) is not list or len(rows) != n
                or frozen+ineligible+errors != n or errors):
            fail("incomplete_or_failed_capture_cohort")
        observed_total += n
        if n == 0:
            if rows:
                fail("unexpected_empty_capture_rows")
            continue
        method = capture.get("candidate_method_sha256")
        if not isinstance(method,str) or method != actual_method_sha:
            fail("candidate_method_changed_or_missing")
        if lock is None:
            lock = method
        elif lock != method:
            fail("candidate_selector_drift")
        for item in rows:
            if not isinstance(item,dict) or item.get("formal") is not False:
                fail("invalid_capture_row")
            code = item.get("race_code")
            if not isinstance(code,str) or not CODE.fullmatch(code) or code in candidates:
                fail("duplicate_or_invalid_race_code")
            candidates[code] = None
            if item.get("status") == "ineligible":
                reason=item.get("reason")
                if not isinstance(reason,str) or not reason:
                    fail("ineligible_missing_reason")
                excluded[reason] += 1
                continue
            if item.get("status") != "frozen_local_before_T_minus_12_research_only":
                fail("unexpected_capture_row_status")
            if code[:8] < "20261107":
                fail("development_race_entered_future_roster")
            file = root/"four_mode_forecasts"/(code+".json")
            if file.is_symlink() or not file.is_file() or file.stat().st_size > 30000:
                fail("original_file_missing_or_unsafe")
            original_bytes=file.read_bytes()
            digest=hashlib.sha256(original_bytes).hexdigest()
            if digest != item.get("source_forecast_sha256"):
                fail("original_first_add_digest_mismatch")
            original=json.loads(original_bytes)
            if (original.get("race_code") != code or original.get("model_version") != VERSION
                    or item.get("remote_first_receipt_of_candidate") is not False
                    or item.get("official_beforeinfo_six_verified") is not False
                    or item.get("official_odds_120_verified") is not False):
                fail("invalid_original_or_claimed_evidence")
            deadline=at_jst(original["deadline_jst"])
            gen=at_jst(original["generated_at_jst"])
            freeze=at_jst(item["frozen_at_jst"])
            observed=datetime.fromisoformat(item["original_observed_at_utc"])
            if (observed.utcoffset()!=timedelta(0)
                    or not gen+timedelta(seconds=1) < observed
                    or not observed+timedelta(seconds=1) < freeze
                    or not gen < freeze < deadline-timedelta(minutes=12)
                    or item.get("deadline_jst") != deadline.isoformat()
                    or item.get("candidate_last_safe_jst") !=
                        (deadline-timedelta(minutes=12)).isoformat()
                    or deadline.strftime("%Y%m%d") != code[:8]):
                fail("candidate_cutoff_or_chronology_unproven")
            expected_base,expected_candidate=candidate_modes(original)
            expected_top1_pair=top1_pair_candidate(original,expected_base)
            if (item.get("baseline") != expected_base or
                    item.get("candidate") != expected_candidate or
                    item.get("top1_pair_candidate") != expected_top1_pair or
                    item.get("top1_pair_rule") != TOP1_PAIR_RULE or
                    item.get("top1_selector_sha256") != method or
                    item.get("mode_selector_sha256") !=
                      {mode:method for mode in SIZES}):
                fail("saved_candidate_not_reproducible")
            candidates[code] = {"deadline":deadline, "baseline":expected_base,
                                "candidate":expected_candidate,
                                "top1_pair_candidate":expected_top1_pair}
    # Excluded races stay in the accounted input population. Do not silently
    # choose the next race to inflate a fixed 600-case reference score.
    return candidates, excluded, observed_total


def miss_classification(tickets, winning):
    if winning in tickets:
        return "covered"
    if not any(x[0] == winning[0] for x in tickets):
        return "winner_head_absent"
    if not any(x[:3] == winning[:3] for x in tickets):
        return "winner_second_pair_absent"
    return "winner_third_absent"


def compare(captures, root):
    # All forecast/candidate replay and cutoff validation occurs before the
    # first confirmed result file is opened.
    candidates, excluded, published = validate_capture_before_any_results(captures,root)
    # An excluded published race is a fixed-cohort slot, not permission to
    # substitute the next frozen race. The deadline order of excluded rows
    # may be unavailable, so fail closed rather than bias the first 600.
    if excluded and any(row is not None for row in candidates.values()):
        fail("incomplete_candidate_roster_no_replacement")
    eligible = [dict(code=code,**row) for code,row in candidates.items() if row]
    eligible.sort(key=lambda r:(r["deadline"],r["code"]))
    selected=eligible[:600]
    counts={phase:{mode:{f"top{n}":{"original":0,"candidate":0,"gained":0,"lost":0,
                                     "denominator":0}
                  for n in TOPS} for mode in SIZES} for phase in ("pilot","confirmation")}
    top1_pair_counts={phase:{mode:{"original":0,"candidate":0,"gained":0,
                                     "lost":0,"denominator":0}
                             for mode in SIZES} for phase in ("pilot","confirmation")}
    missing=[]
    invalid=Counter()
    valid=Counter()
    breakdown={phase:{mode:{"covered":0,"winner_head_absent":0,
                             "winner_second_pair_absent":0,"winner_third_absent":0}
                      for mode in SIZES} for phase in ("pilot","confirmation")}
    for index,row in enumerate(selected):
        code=row["code"]
        path=Path(root)/"confirmed_results"/(code+".json")
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 20000:
            missing.append(code)
            continue
        try:
            # Apply the same saved-result trust gate as the existing collector.
            # A plausible finish and an arbitrary https URL are not enough.
            if not confirmed_record_is_usable(path,code):
                raise ValueError("result_failed_collector_trust_gate")
            result=json.loads(path.read_bytes())
            finish=result["finish_order"]
            source_sha=result.get("source_sha256")
            if (result.get("race_code") != code or result.get("status") != "confirmed"
                    or type(finish) is not list or len(finish)!=3
                    or any(type(n) is not int or not 1<=n<=6 for n in finish)
                    or len(set(finish))!=3
                    or not isinstance(source_sha,str) or not SHA64.fullmatch(source_sha)
                    or not isinstance(result.get("source_url"),str)
                    or not result["source_url"].startswith("https://")
                    or at_jst(result["confirmed_at_jst"]) <= row["deadline"]
                    # Collector permits up to 3 minutes of source/collection
                    # timestamp skew for coverage. Research scoring requires
                    # the later persisted collection to follow source receipt.
                    or at_jst(result["collected_at_jst"]) <
                        at_jst(result["confirmed_at_jst"])):
                raise ValueError("result_not_independently_usable")
        except (OSError,KeyError,TypeError,ValueError,UnicodeError):
            invalid["invalid_result_content_or_time"]+=1
            continue
        phase="pilot" if index < 300 else "confirmation"
        valid[phase]+=1
        winning="-".join(map(str,finish))
        for mode in SIZES:
            old=row["baseline"][mode]
            new=row["candidate"][mode]
            pair=row["top1_pair_candidate"][mode]
            if any(set(old[:n]) != set(pair[:n]) for n in (2,3,5,10)):
                fail("top1_pair_changed_ticket_membership")
            t=top1_pair_counts[phase][mode]
            old_top1=winning==old[0]
            pair_top1=winning==pair[0]
            t["original"]+=int(old_top1)
            t["candidate"]+=int(pair_top1)
            t["gained"]+=int(pair_top1 and not old_top1)
            t["lost"]+=int(old_top1 and not pair_top1)
            breakdown[phase][mode][miss_classification(old,winning)]+=1
            for n in TOPS:
                stats=counts[phase][mode][f"top{n}"]
                a=winning in old[:n]
                b=winning in new[:n]
                stats["original"]+=int(a)
                stats["candidate"]+=int(b)
                stats["gained"]+=int(b and not a)
                stats["lost"]+=int(a and not b)
    for phase in top1_pair_counts:
        for mode, stat in top1_pair_counts[phase].items():
            stat["denominator"]=valid[phase]
            stat["original_pct"]=(round(100*stat["original"]/valid[phase],2)
                                  if valid[phase] else None)
            stat["candidate_pct"]=(round(100*stat["candidate"]/valid[phase],2)
                                   if valid[phase] else None)
            if stat["candidate"]-stat["original"] != stat["gained"]-stat["lost"]:
                fail("top1_pair_arithmetic_mismatch")
    for phase in counts:
        for mode in SIZES:
            for n in TOPS:
                row=counts[phase][mode][f"top{n}"]
                row["denominator"]=valid[phase]
                row["original_pct"]=round(100*row["original"]/valid[phase],2) if valid[phase] else None
                row["candidate_pct"]=round(100*row["candidate"]/valid[phase],2) if valid[phase] else None
                if row["candidate"]-row["original"] != row["gained"]-row["lost"]:
                    fail("paired_arithmetic_mismatch")
    return {
        "schema":"FOUR_MODE_ALL_SHADOW_SAME_RACE_REVIEW_V1",
        "status":"reference_only_no_prospective_certification",
        "formal":False,"candidate_first_remote_receipt_verified":False,
        "complete_capture_run_inventory_verified":False,
        "model_improvement_proven":False,"model_promotion_allowed":False,
        "published_capture_races":published,"frozen_future_races_total":len(eligible),
        "selected_first_600_frozen":len(selected),
        "excluded_originally_captured":dict(excluded),
        "confirmed_result_matches":dict(valid),"missing_result_codes":missing,
        "invalid_result_counts":dict(invalid),
        "topn_by_phase":counts,"top1_pair_by_phase":top1_pair_counts,
        "top1_pair_policy":TOP1_PAIR_RULE,
        "top1_pair_top3_5_10_memberships_preserved":True,
        "original_full_ticket_miss_by_phase":breakdown,
        "warning":"A verified local same-job freeze is reference evidence only. Never claim independent FIRST remote receipt for candidate, official T12 complete data, or generalizable improvement. No selection based on results.",
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root",type=Path,default=Path("."))
    p.add_argument("--capture",type=Path,action="append",default=[])
    p.add_argument("--output",type=Path)
    a=p.parse_args()
    if not a.capture:
        output={"status":"no_frozen_future_captures_supplied","formal":False,
                "model_improvement_proven":False,"model_promotion_allowed":False}
    else:
        documents=[json.loads(path.read_bytes()) for path in a.capture]
        output=compare(documents,a.root)
    json_text=json.dumps(output,ensure_ascii=False,sort_keys=True,indent=2)+"\n"
    if a.output:
        a.output.write_text(json_text,encoding="utf-8")
    else:
        print(json_text,end="")


if __name__=="__main__":
    main()
