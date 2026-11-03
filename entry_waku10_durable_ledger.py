"""Append-only publication of separate, experimental T−2 Waku10 comparisons.

Stores research picks on entry-course-evidence-ledger/waku10/, not formal modes.
Does not certify independent remote first-seen timing; GitHub write-readback is
only proof of identical bytes being present when the publisher read them.
"""
from datetime import datetime, timezone
from itertools import permutations
import hashlib
import json
import re
from entry_waku10_pilot import PROTOCOL

VALID={"-".join(map(str,p)) for p in permutations(range(1,7),3)}
HEX=re.compile("[a-f0-9]{64}\\Z")
RACE=re.compile("20[0-9]{10}\\Z")
REQUIRED_SOURCES={"third_party_preview_stt","third_party_preview_tkz",
                  "third_party_race_card","third_party_waku10"}


def _at(text):
    if type(text) is not str:
        return None
    try:
        t=datetime.fromisoformat(text)
        return t if t.utcoffset() is not None else None
    except ValueError:
        return None


def validate_waku10_archive(raw, *, now=None):
    if type(raw) is not bytes or not raw or len(raw)>120_000:
        raise ValueError("waku10_archive_bytes_invalid")
    try:
        item=json.loads(raw)
    except (ValueError,UnicodeError) as exc:
        raise ValueError("waku10_archive_json_invalid") from exc
    if (type(item) is not dict or
            item.get("schema")!="entry-waku10-late-preview-pilot-v1" or
            item.get("protocol")!=PROTOCOL or
            item.get("research_only") is not True or
            item.get("forecast_record") is not True or
            item.get("formal") is not False or
            item.get("calibrated") is not False or
            item.get("not_equivalent_to_t12") is not True or
            item.get("frame_st_is_not_course_st") is not True or
            item.get("independent_remote_first_seen_verified") is not False):
        raise ValueError("waku10_archive_header_invalid")
    code=item.get("race_code")
    if type(code) is not str or not RACE.fullmatch(code):
        raise ValueError("waku10_archive_race_invalid")
    frozen=_at(item.get("frozen_at"))
    written=_at(item.get("write_received_at"))
    cutoff=_at(item.get("cutoff_at"))
    reference=_at(item.get("reference_baseline_cutoff_at"))
    now=now or datetime.now(timezone.utc)
    if (not all((frozen,written,cutoff,reference)) or
            now.utcoffset() is None or not reference<frozen<=written<cutoff
            or now>=cutoff):
        raise ValueError("waku10_archive_not_pre_cutoff")
    entry=item.get("entry")
    if (type(entry) is not list or len(entry)!=6 or
            any(type(n) is not int for n in entry) or
            set(entry)!=set(range(1,7))):
        raise ValueError("waku10_archive_entry_invalid")
    counts=item.get("sample_counts")
    minimum=item.get("min_course_starts")
    if (type(counts) is not dict or set(counts)!={str(i) for i in range(1,7)}
            or type(minimum) is not int or not 8<=minimum<=10 or
            any(type(c) is not int or c<minimum or c>10 for c in counts.values())):
        raise ValueError("waku10_archive_samples_insufficient")
    for key in ("baseline","waku10_course","waku10_course_plus_frame_st_proxy"):
        tickets=item.get(key)
        if type(tickets) is not list or len(tickets)!=120 or set(tickets)!=VALID or len(set(tickets))!=120:
            raise ValueError("waku10_archive_ranking_invalid")
    receipts=item.get("source_receipts")
    if type(receipts) is not list or len(receipts)!=4:
        raise ValueError("waku10_archive_missing_receipts")
    sources=set()
    for r in receipts:
        if type(r) is not dict or type(r.get("source")) is not str:
            raise ValueError("waku10_archive_bad_receipt")
        observed=_at(r.get("received_at"))
        if (not observed or observed>frozen or
                not HEX.fullmatch(str(r.get("sha256") or ""))):
            raise ValueError("waku10_archive_late_or_invalid_receipt")
        sources.add(r["source"])
    if sources!=REQUIRED_SOURCES:
        raise ValueError("waku10_archive_wrong_sources")
    return f"waku10/{code[:8]}/{code}.json"


def publish_waku10(raw, remote_read, remote_create, *, clock=None):
    now=clock or (lambda:datetime.now(timezone.utc))
    path=validate_waku10_archive(raw,now=now())
    old=remote_read(path)
    if old is not None and old!=raw:
        raise ValueError("waku10_immutable_archive_collision")
    if old is None:
        remote_create(path,raw)
        status="new_append_only_waku10_pilot"
    else:
        status="already_identical_waku10_pilot"
    if remote_read(path)!=raw:
        raise ValueError("waku10_archive_readback_mismatch")
    if now()>=_at(json.loads(raw)["cutoff_at"]):
        raise ValueError("waku10_archive_published_after_cutoff")
    return {"status":status,"stored":True,"path":path,
            "branch":"entry-course-evidence-ledger","sha256":hashlib.sha256(raw).hexdigest(),
            "research_only":True,"formal":False,
            "independent_remote_first_seen_verified":False}
