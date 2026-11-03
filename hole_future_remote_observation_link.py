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


def match(future,first_add,ledger_root,forecast_root):
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
            rows=document["records"]
            if (document["schema"]!="FOUR_MODE_GITHUB_REMOTE_OBSERVATION_V1"
                    or document["formal"] is not False
                    or document["independent_first_remote_receipt_verified"] is not False
                    or document["github_server_observation_not_first_receipt"] is not True
                    or len(rows)!=document["publication_count"]):
                raise ValueError("invalid_ledger_header")
            sha=document["publication_commit_sha"]
            if type(sha) is not str or SHA.fullmatch(sha) is None:
                raise ValueError("invalid_ledger_sha")
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
    return {
        "schema":"HOLE_FUTURE_REMOTE_OBSERVATION_LINK_V1",
        "status":"observational_research_linkage_only",
        "comparable":len(codes),
        "evidence_status_counts":{key:tally[key] for key in KNOWN},
        "race_status":result,"excluded_ledger_files":dict(invalid_files),
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
