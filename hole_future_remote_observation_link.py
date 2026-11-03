"""Reconcile archived GitHub server observations with frozen future hole races.

Only strict provenance-linked observations enter the evidence-backed *research*
subset. This is not independent first receipt and NEVER formal accuracy.
"""
import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import datetime,timedelta,timezone
from pathlib import Path

from hole_future_locked_eval import FIRST_ELIGIBLE_DAY

CODE=re.compile(r"20[0-9]{10}\Z")
SHA=re.compile(r"[a-f0-9]{40}\Z")
HEX=re.compile(r"[a-f0-9]{64}\Z")
JST=timezone(timedelta(hours=9))
KNOWN=("observed_before_t12","observed_after_t12",
       "missing_observation","conflicting_observations","invalid_observation",
       "local_git_first_add_unverified")


def validated_ledger(document, path):
    """A malformed receipt must never contribute a verified race."""
    if (not isinstance(document,dict)
            or document.get("schema")!="FOUR_MODE_GITHUB_REMOTE_OBSERVATION_V1"
            or document.get("status")!="remote_observation_audited_nonformal"
            or document.get("formal") is not False
            or document.get("independent_first_remote_receipt_verified") is not False
            or document.get("github_server_observation_not_first_receipt") is not True
            or document.get("production_forecast_changed") is not False):
        raise ValueError("invalid_ledger_header")
    count=document.get("publication_count")
    sha=document.get("publication_commit_sha")
    rows=document.get("records")
    if (type(count) is not int or not 1<=count<=500
            or type(sha) is not str or SHA.fullmatch(sha) is None
            or not isinstance(rows,list) or len(rows)!=count):
        raise ValueError("invalid_ledger_roster")
    day=path.parent.name
    if not re.fullmatch(r"20[0-9]{6}",day):
        raise ValueError("invalid_ledger_day")
    seen=set()
    statuses=Counter()
    for row in rows:
        if not isinstance(row,dict):
            raise ValueError("invalid_ledger_row")
        code=row.get("race_code")
        state=row.get("status")
        if (type(code) is not str or CODE.fullmatch(code) is None
                or code[:8]!=day or code in seen
                or row.get("first_add_commit")!=sha
                or state not in (
                    "github_server_observed_before_t_minus_12",
                    "github_server_observed_after_t_minus_12",
                    "remote_observation_unverified")):
            raise ValueError("invalid_ledger_race_or_status")
        seen.add(code)
        statuses[state]+=1
    for state,key in (
        ("github_server_observed_before_t_minus_12","observed_before_t_minus_12"),
        ("github_server_observed_after_t_minus_12","observed_after_t_minus_12"),
        ("remote_observation_unverified","unverified_count"),
    ):
        if type(document.get(key)) is not int or document[key]!=statuses[state]:
            raise ValueError("invalid_ledger_status_counts")
    return sha,rows

def match(future,first_add,ledger_root,forecast_root):
    # The 2026-11-03 job runs before the locked cohort's first eligible day.
    # An empty not-yet-eligible verdict has no prospective proof fields.
    if future.get("status")=="not_yet_eligible":
        if future.get("formal") is not False or future.get("comparable")!=0:
            raise ValueError("invalid_pre_eligible_verdict")
        future={**future,"independent_first_receipt_verified":False,
                "race_codes":[]}
    if (future.get("formal") is not False or
            future.get("independent_first_receipt_verified") is not False or
            first_add.get("formal") is not False or
            first_add.get("independent_remote_first_receipt_verified") is not False):
        raise ValueError("invalid_evidence_header")
    codes=future.get("race_codes",[])
    if type(codes) is not list or len(set(codes))!=len(codes) or not all(
            type(c) is str and CODE.fullmatch(c) and c[:8]>=FIRST_ELIGIBLE_DAY.strftime("%Y%m%d")
            for c in codes):
        raise ValueError("invalid_comparable_race_codes")
    first={}
    for entry in first_add.get("records",[]):
        code=entry.get("race_code")
        if code in first:raise ValueError("duplicate_first_add_code")
        first[code]=entry
    root=Path(ledger_root)
    forecasts=Path(forecast_root)
    candidates={}
    invalid_files=Counter()
    folder=root/"github_server"
    for path in sorted(folder.glob("20??????/run-*-attempt-*.json")) if folder.is_dir() else []:
        if path.is_symlink() or not path.is_file() or path.stat().st_size>2_000_000:
            invalid_files["unsafe_ledger_file"]+=1;continue
        try:
            document=json.loads(path.read_bytes())
            sha,rows=validated_ledger(document,path)
            for entry in rows:
                code=entry.get("race_code")
                if code not in codes:continue
                candidates.setdefault(code,[]).append((sha,entry))
        except (ValueError,TypeError,KeyError,OSError,UnicodeError):
            invalid_files["invalid_ledger_file"]+=1
    result={};tally=Counter()
    for code in codes:
        path=forecasts/"four_mode_forecasts"/(code+".json")
        local=first.get(code)
        verdict="missing_observation"
        entries=candidates.get(code,[])
        if not isinstance(local,dict) or (
                local.get("status")!="local_git_first_add_clock_before_t12_unverified"):
            verdict="local_git_first_add_unverified"
        elif entries:
            if path.is_symlink() or not path.is_file() or path.stat().st_size>30000:
                verdict="invalid_observation"
            else:
                digest=hashlib.sha256(path.read_bytes()).hexdigest()
                trusted=[]
                bad=False
                for sha,item in entries:
                    state=item.get("status")
                    if (sha!=local.get("first_add_commit")
                            or item.get("first_add_commit")!=sha):
                        bad=True;continue
                    if state=="remote_observation_unverified":
                        continue
                    if (state not in (
                            "github_server_observed_before_t_minus_12",
                            "github_server_observed_after_t_minus_12")
                            or item.get("first_add_blob_matches_remote") is not True
                            or item.get("original_sha256")!=digest
                            or item.get("original_sha256")!=local.get("source_sha256")):
                        bad=True;continue
                    try:
                        observed=datetime.fromisoformat(item["github_api_server_date_utc"])
                        cutoff=datetime.fromisoformat(item["deadline_minus_12_jst"])
                        source=json.loads(path.read_bytes())
                        deadline=datetime.fromisoformat(source["deadline_jst"])
                        if (observed.utcoffset()!=timedelta(0)
                                or cutoff.utcoffset()!=timedelta(hours=9)
                                or cutoff!=deadline-timedelta(minutes=12)):
                            raise ValueError("inconsistent_date")
                        classified=("github_server_observed_before_t_minus_12"
                                    if observed<cutoff else
                                    "github_server_observed_after_t_minus_12")
                        if state!=classified:
                            raise ValueError("false_observation_label")
                        trusted.append((observed,state))
                    except (KeyError,ValueError,TypeError,UnicodeError,OSError):
                        bad=True
                if bad:
                    verdict="conflicting_observations"
                elif trusted:
                    first_seen=min(trusted,key=lambda value:value[0])
                    verdict=("observed_before_t12" if first_seen[1]==
                             "github_server_observed_before_t_minus_12" else
                             "observed_after_t12")
                else:
                    verdict="invalid_observation"
        tally[verdict]+=1
        result[code]=verdict
    if sum(tally.values())!=len(codes):
        raise ValueError("remote_link_denominator_mismatch")
    # Post-outcome reporting: no hit information is used to infer evidence.
    # All comparable races are partitioned, including those without proof.
    from hole_future_locked_eval import POLICIES,TOPS
    flags=future.get("race_flags",{})
    if not isinstance(flags,dict) or set(flags)!=set(codes):
        if not codes and flags=={}:
            pass
        else:
            raise ValueError("outcome_flags_missing_or_mismatched")
    strata={state:{"races":0,"hits":{p:{f"top{k}":0 for k in TOPS}
                                 for p in POLICIES}} for state in KNOWN}
    for code in codes:
        state=result[code]
        group=strata[state]
        group["races"]+=1
        for policy in POLICIES:
            policy_flags=flags[code].get(policy)
            if not isinstance(policy_flags,dict):
                raise ValueError("missing_policy_flags")
            previous=False
            for k in TOPS:
                key=f"top{k}"
                hit=policy_flags.get(key)
                if type(hit) is not bool or (previous and not hit):
                    raise ValueError("invalid_topn_flags")
                group["hits"][policy][key]+=int(hit)
                previous=hit
    if sum(group["races"] for group in strata.values())!=len(codes):
        raise ValueError("stratum_denominator_mismatch")
    total_hits=future.get("hits")
    if codes:
        if not isinstance(total_hits,dict):
            raise ValueError("missing_full_cohort_hits")
        for p in POLICIES:
            for k in TOPS:
                key=f"top{k}"
                if sum(group["hits"][p][key] for group in strata.values())!=total_hits[p][key]:
                    raise ValueError("stratum_hit_reconciliation")
    return {
        "schema":"HOLE_FUTURE_REMOTE_OBSERVATION_LINK_V1",
        "status":"observational_research_linkage_only",
        "comparable":len(codes),
        "evidence_status_counts":{key:tally[key] for key in KNOWN},
        "race_status":result,"excluded_ledger_files":dict(invalid_files),
        "topn_by_evidence_status":strata,
        "remote_observed_before_t12_count":tally["observed_before_t12"],
        "independent_first_remote_receipt_verified":False,
        "formal":False,"production_forecast_changed":False,
        "locked_selector_changed":False,
        "warning":"A GitHub API observed-before-T12 result means exact bytes "
                  "were visible at that observation, not independently proven "
                  "first received then. No formal rate or promotion."
    }


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--root",type=Path,default=Path("."))
    parser.add_argument("--ledger",type=Path,default=Path("remote-observation-ledger"))
    parser.add_argument("--future",type=Path,default=Path("hole_future_locked_results.json"))
    parser.add_argument("--first-add",type=Path,default=Path("hole_future_first_add_results.json"))
    args=parser.parse_args()
    report=match(json.loads(args.future.read_text()),json.loads(args.first_add.read_text()),
                 args.ledger,args.root)
    print(json.dumps(report,ensure_ascii=False,sort_keys=True))

if __name__=="__main__":main()
