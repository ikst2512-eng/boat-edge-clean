"""Inspect GitHub first-add history of separate research evidence files.

GitHub commit SHA + 'added' file status proves the file entered the branch
in a concrete historical commit. Commit committer timestamps are NOT
independently authenticated GitHub reception times and must not certify
a prospective pre-cutoff forecast. This module never edits the ledger.
"""
from datetime import datetime,timezone
from urllib.parse import urlencode
import re

SHA=re.compile(r"[0-9a-f]{40}\\Z")
PATH=re.compile(r"(?:t12_baselines|waku10|entry_course)/20[0-9]{6}/20[0-9]{10}\\.json\\Z")
BRANCH="entry-course-evidence-ledger"
MAX_FILES=12
MAX_PAGES=3


def _time(value):
    if not isinstance(value,str):
        return None
    try:
        at=datetime.fromisoformat(value.replace("Z","+00:00"))
        return at if at.utcoffset() is not None else None
    except ValueError:
        return None


def first_add_for_path(path, *, cutoff_at, fetch, repository):
    if type(path) is not str or not PATH.fullmatch(path):
        raise ValueError("first_add_bad_path")
    cutoff=_time(cutoff_at)
    if cutoff is None:
        raise ValueError("first_add_bad_cutoff")
    oldest=None
    pages=0
    for page in range(1,MAX_PAGES+1):
        args=urlencode({"sha":BRANCH,"path":path,"per_page":100,"page":page})
        commits=fetch(f"repos/{repository}/commits?{args}")
        if type(commits) is not list:
            raise ValueError("first_add_history_response_invalid")
        if not commits and page==1:
            return {"path":path,"status":"history_missing","first_add_sha":None,
                    "commit_timestamp_before_cutoff":False,
                    "independent_server_first_seen_verified":False}
        for entry in commits:
            if not isinstance(entry,dict) or not SHA.fullmatch(str(entry.get("sha") or "")):
                raise ValueError("first_add_history_sha_invalid")
        if commits:
            oldest=commits[-1]["sha"]
        pages=page
        if len(commits)<100:
            break
    else:
        return {"path":path,"status":"history_pagination_incomplete",
                "first_add_sha":None,"commit_timestamp_before_cutoff":False,
                "independent_server_first_seen_verified":False}
    detail=fetch(f"repos/{repository}/commits/{oldest}")
    if not isinstance(detail,dict) or detail.get("sha")!=oldest or type(detail.get("files")) is not list:
        raise ValueError("first_add_commit_detail_invalid")
    entries=[item for item in detail["files"] if isinstance(item,dict) and item.get("filename")==path]
    if len(entries)!=1 or entries[0].get("status")!="added":
        return {"path":path,"status":"earliest_change_not_addition",
                "first_add_sha":oldest,"commit_timestamp_before_cutoff":False,
                "independent_server_first_seen_verified":False}
    metadata=detail.get("commit")
    committer=metadata.get("committer") if isinstance(metadata,dict) else None
    commit_time=_time(committer.get("date")) if isinstance(committer,dict) else None
    if commit_time is None:
        return {"path":path,"status":"first_add_commit_time_missing",
                "first_add_sha":oldest,"commit_timestamp_before_cutoff":False,
                "independent_server_first_seen_verified":False}
    return {"path":path,"status":"first_add_commit_observed",
            "first_add_sha":oldest,
            "commit_committer_time":commit_time.isoformat(),
            "cutoff_at":cutoff.isoformat(),
            "commit_timestamp_before_cutoff":commit_time<cutoff,
            "time_basis":"git_commit_committer_date_not_independent_server_reception",
            "independent_server_first_seen_verified":False}


def audit_first_add(validated, *, fetch, repository, limit=MAX_FILES):
    if type(limit) is not int or not 1<=limit<=MAX_FILES:
        raise ValueError("first_add_limit_invalid")
    if type(validated) is not list:
        raise ValueError("first_add_validated_items_invalid")
    records=[]
    errors=[]
    # Reject untrusted payloads before performing any API reads; only
    # SHA-checked, internally validated paths can reach this stage.
    selected=sorted(validated,key=lambda item:item["path"])[:limit]
    for item in selected:
        try:
            outcome=first_add_for_path(item["path"],cutoff_at=item["cutoff_at"].isoformat(),
                                       fetch=fetch,repository=repository)
            records.append(outcome)
        except (OSError,ValueError,TypeError,KeyError) as exc:
            errors.append({"path":item["path"],"error_type":type(exc).__name__})
    return {"checked_count":len(records),
            "unexamined_due_to_limit":max(0,len(validated)-limit),
            "first_add_commit_found_count":sum(x["status"]=="first_add_commit_observed" for x in records),
            "commit_timestamp_before_cutoff_count":sum(x.get("commit_timestamp_before_cutoff",False) for x in records),
            "failed_or_incomplete_history_count":len(errors)+sum(x["status"]!="first_add_commit_observed" for x in records),
            "records":records,"errors":errors,
            "independently_verified_first_seen_count":0,
            "note":"Git committer date may be set by commit author. No authenticated server-received timestamp is established.",
            "research_only":True,"formal":False}
