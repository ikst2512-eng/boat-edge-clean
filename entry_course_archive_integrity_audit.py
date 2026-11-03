"""Read-only retrospective inspection of immutable research archive BYTES.

This validates Git blob identity, model payload shape, internal as-of clocks,
source digests and T−12 reference matching. It deliberately does NOT establish
a GitHub-server-timestamped first addition before the cutoff. Thus these
records must never be called independently certified prospective forecasts.
"""
import base64
from datetime import datetime, timedelta
import hashlib
import json
import re

from entry_course_t12_seed import validate_base, _dt
from entry_course_durable_ledger import prepare
from entry_waku10_durable_ledger import validate_waku10_archive, _at

SHA=re.compile(r"[0-9a-f]{40}\Z")
RACE=re.compile(r"20[0-9]{10}\Z")
MAX_BYTES=150_000


def _read_blob(blob_sha, fetch, repository):
    if not isinstance(blob_sha,str) or not SHA.fullmatch(blob_sha):
        raise ValueError("archive_missing_tree_blob_sha")
    item=fetch(f"repos/{repository}/git/blobs/{blob_sha}")
    if (type(item) is not dict or item.get("encoding")!="base64" or
            type(item.get("content")) is not str):
        raise ValueError("archive_bad_blob_response")
    try:
        raw=base64.b64decode(item["content"],validate=False)
    except (ValueError,TypeError) as exc:
        raise ValueError("archive_blob_not_base64") from exc
    if not raw or len(raw)>MAX_BYTES:
        raise ValueError("archive_blob_size_invalid")
    actual=hashlib.sha1(b"blob "+str(len(raw)).encode("ascii")+b"\x00"+raw).hexdigest()
    if actual!=blob_sha or (item.get("sha") and item.get("sha")!=blob_sha):
        raise ValueError("archive_blob_identity_mismatch")
    return raw


def _validate_one(path, raw, *, day):
    parts=path.split("/")
    if len(parts)!=3 or parts[1]!=day or not parts[2].endswith(".json"):
        raise ValueError("archive_invalid_path")
    code=parts[2][:-5]
    if not RACE.fullmatch(code) or code[:8]!=day:
        raise ValueError("archive_bad_race_code")
    try:
        obj=json.loads(raw)
    except (ValueError,UnicodeError) as exc:
        raise ValueError("archive_json_invalid") from exc
    if type(obj) is not dict:
        raise ValueError("archive_payload_not_object")
    if obj.get("race_code")!=code:
        raise ValueError("archive_race_mismatch")
    kind=parts[0]
    if kind=="t12_baselines":
        cutoff=_dt(obj.get("cutoff_jst"))
        if not cutoff:
            raise ValueError("archive_t12_cutoff_missing")
        expected=f"t12_baselines/{day}/{code}.json"
        actual=validate_base(raw,code,now=cutoff-timedelta(microseconds=1))
        if actual!=expected:
            raise ValueError("archive_t12_path_mismatch")
        return {"code":code,"family":"t12","cutoff_at":cutoff,
                "reference_t12_top10":obj.get("predictions")}
    if kind in ("waku10","entry_course"):
        cutoff=_at(obj.get("cutoff_at"))
        if not cutoff:
            raise ValueError("archive_t2_cutoff_missing")
        simulated_before=cutoff-timedelta(microseconds=1)
        actual=(validate_waku10_archive(raw,now=simulated_before)
                if kind=="waku10" else prepare(raw,now=simulated_before))
        if actual!=path:
            raise ValueError("archive_t2_path_mismatch")
        return {"code":code,"family":kind,"cutoff_at":cutoff,
                "reference_t12_cutoff_at":_at(obj.get("reference_baseline_cutoff_at")),
                "reference_t12_top10":obj.get("reference_t12_top10")}
    raise ValueError("archive_unrecognized_family")


def audit_archive_bytes(day, tree, fetch, *, repository):
    if type(tree) is not list:
        raise ValueError("archive_tree_not_list")
    decoded=[]
    failures=[]
    for item in tree:
        if not isinstance(item,dict) or item.get("type")!="blob":
            continue
        path=item.get("path")
        if (type(path) is not str or not any(
                path.startswith(f"{family}/{day}/")
                for family in ("t12_baselines","waku10","entry_course"))):
            continue
        try:
            raw=_read_blob(item.get("sha"),fetch,repository)
            validated=_validate_one(path,raw,day=day)
            validated["path"]=path
            decoded.append(validated)
        except (ValueError,KeyError,TypeError,UnicodeError,OSError) as exc:
            failures.append({"path":path,"reason":str(exc)[:110]
                             if isinstance(exc,ValueError)
                             else type(exc).__name__})
    t12={item["code"]:item for item in decoded if item["family"]=="t12"}
    linked=[]
    unlinked=[]
    for item in decoded:
        if item["family"]=="t12":
            continue
        original=t12.get(item["code"])
        if (original is None or
                original["cutoff_at"]!=item["reference_t12_cutoff_at"] or
                original["reference_t12_top10"]!=item["reference_t12_top10"]):
            unlinked.append(item["path"])
        else:
            linked.append(item["path"])
    return {
        "blob_sha_and_internal_payload_valid_count":len(decoded),
        "internally_validated_paths":[{"path":x["path"],"cutoff_at":x["cutoff_at"].isoformat()}
                                      for x in decoded],
        "t12_payload_valid_count":len(t12),
        "t2_payload_valid_count":sum(x["family"]!="t12" for x in decoded),
        "t2_reference_matched_count":len(linked),
        "t2_reference_unmatched_count":len(unlinked),
        "t2_reference_matched_paths":linked,
        "t2_reference_unmatched_paths":unlinked,
        "invalid_blob_or_payload_count":len(failures),
        "invalid_blob_or_payload":failures,
        "internal_asof_clock_checked":True,
        "git_blob_sha_verified":True,
        "independent_remote_first_add_time_verified":False,
        "pre_cutoff_git_publication_verified":False,
        "research_only":True,"formal":False
    }
