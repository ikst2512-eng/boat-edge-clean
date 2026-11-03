"""Source-backed Waku10 evidence with strict lane-vs-course separation.

BoatraceCSV Waku10 is a pre-race snapshot: latest ten starts for the CURRENT
frame, with actual-entry overrides. Its frame-average ST is NOT a course-ST
history. It must never be silently substituted for the strict 31-day
individual-course/result history used by entry_course_history.py.
"""
from datetime import datetime, timezone
from urllib.request import Request, urlopen
import csv
import hashlib
import io
import math
import re

URL_ROOT="https://boatracecsv.github.io/data/programs/waku10/"
VALID_CODE=re.compile(r"20[0-9]{10}\Z")
HASH=re.compile(r"[a-f0-9]{64}\Z")
MAX_BYTES=2_000_000


def _when(s):
    if not isinstance(s,str):
        return None
    try:
        value=datetime.fromisoformat(s)
        return value if value.utcoffset() is not None else None
    except ValueError:
        return None


def _name(value):
    return re.sub(r"\s+","",value) if isinstance(value,str) else None


def fetch_waku10(target_code, *, cutoff_at, fetch=None, clock=None):
    if type(target_code) is not str or not VALID_CODE.fullmatch(target_code):
        raise ValueError("waku10_invalid_race")
    cutoff=_when(cutoff_at)
    if cutoff is None:
        raise ValueError("waku10_invalid_cutoff")
    now=clock or (lambda:datetime.now(timezone.utc))
    if now()>=cutoff:
        raise ValueError("waku10_requested_after_cutoff")
    day=target_code[:8]
    url=f"{URL_ROOT}{day[:4]}/{day[4:6]}/{day[6:8]}.csv"
    if fetch is None:
        def fetch(url):
            if not url.startswith(URL_ROOT):
                raise ValueError("waku10_untrusted_source_url")
            with urlopen(Request(url,headers={"User-Agent":"BOAT-EDGE-CLEAN-RESEARCH/1.0"}),timeout=5) as response:
                if response.status!=200:
                    raise ValueError("waku10_bad_http")
                return response.read(MAX_BYTES+1)
    raw=fetch(url)
    received=now()
    if received.utcoffset() is None or received>=cutoff:
        raise ValueError("waku10_received_after_cutoff")
    if type(raw) is not bytes or not raw or len(raw)>MAX_BYTES:
        raise ValueError("waku10_invalid_csv_size")
    try:
        reader=csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
        if not reader.fieldnames or "レースコード" not in reader.fieldnames:
            raise ValueError("waku10_csv_header_invalid")
        matches=[r for r in reader if r.get("レースコード")==target_code]
    except (UnicodeError,csv.Error) as exc:
        raise ValueError("waku10_csv_unreadable") from exc
    if len(matches)!=1:
        raise ValueError("waku10_missing_or_duplicate_race")
    return {"race_code":target_code,"source":"BoatraceCSV third-party Waku10 pre-race",
            "source_url":url,"received_at":received.isoformat(),
            "sha256":hashlib.sha256(raw).hexdigest(),"row":matches[0],
            "research_only":True,"official_source_verified":False}


def extract_waku10_course_evidence(target, evidence, entry, *, frozen_at, min_course_starts=8):
    """A bounded per-race historical lane source, never individual-course ST."""
    if not isinstance(target,dict) or not isinstance(evidence,dict):
        raise ValueError("waku10_invalid_inputs")
    code=target.get("race_key","").replace("-","")
    if (type(code) is not str or not VALID_CODE.fullmatch(code)
            or evidence.get("race_code")!=code
            or evidence.get("research_only") is not True
            or evidence.get("official_source_verified") is not False
            or not HASH.fullmatch(str(evidence.get("sha256") or ""))):
        raise ValueError("waku10_wrong_race_or_provenance")
    received=_when(evidence.get("received_at"))
    frozen=_when(frozen_at)
    if not received or not frozen or received>frozen:
        raise ValueError("waku10_source_after_freeze")
    if (type(entry) not in (tuple,list) or len(entry)!=6 or
            any(type(x) is not int for x in entry) or set(entry)!=set(range(1,7))):
        raise ValueError("waku10_invalid_entry")
    if type(min_course_starts) is not int or not 1<=min_course_starts<=10:
        raise ValueError("waku10_invalid_threshold")
    racers=target.get("racers")
    if type(racers) is not list or len(racers)!=6 or set(r.get("lane") for r in racers if isinstance(r,dict))!=set(range(1,7)):
        raise ValueError("waku10_target_racers_invalid")
    mapping={r["lane"]:r for r in racers}
    row=evidence.get("row")
    if type(row) is not dict:
        raise ValueError("waku10_source_row_invalid")
    result=[]
    for course,boat in enumerate(entry,1):
        racer=mapping[boat]
        if (_name(racer.get("name")) is None or
                _name(racer.get("name"))!=_name(row.get(f"艇{boat}_選手名")) or
                not re.fullmatch(r"[0-9]{4}",str(racer.get("registration_no") or ""))):
            raise ValueError("waku10_racer_identity_mismatch")
        sample=[]
        for slot in range(1,11):
            key=f"艇{boat}_過去{slot}走_"
            rank=str(row.get(key+"着順") or "").strip()
            raw_course=str(row.get(key+"進入") or "").strip()
            if not rank:
                if raw_course:
                    raise ValueError("waku10_empty_rank_with_course")
                continue
            # Blank 進入 means frame-nari according to documented Waku10 source.
            hist_course=boat if not raw_course else int(raw_course) if raw_course in ("1","2","3","4","5","6") else None
            if hist_course is None:
                raise ValueError("waku10_invalid_past_course")
            if rank in ("1","2","3","4","5","6") and hist_course==course:
                sample.append(int(rank))
        wins=sum(x==1 for x in sample)
        top2=sum(x<=2 for x in sample)
        top3=sum(x<=3 for x in sample)
        n=len(sample)
        try:
            avg=float(row[f"艇{boat}_枠番別平均ST"])
        except (ValueError,TypeError,KeyError):
            avg=None
        if avg is not None and (not math.isfinite(avg) or not 0<=avg<=0.5):
            avg=None
        result.append({"boat":boat,"course":course,"registration_no":str(racer["registration_no"]),
            "frame":boat,"frameRecent10Slots":10,
            "matchedCourseCompletedRuns":n,
            "courseWinRate":wins/n if n else None,
            "courseTop2Rate":top2/n if n else None,
            "courseTop3Rate":top3/n if n else None,
            "courseAverageST":None,
            "frameAverageSTProxy":avg,
            "sufficient_sample":n>=min_course_starts,
            "source":"third_party_waku10_frame_history",
            "course_histories_are_not_independently_result_joined":True})
    return {"race_code":code,"entry":list(entry),"rows":result,
            "all_course_samples_sufficient":all(r["sufficient_sample"] for r in result),
            "research_only":True,"formal_forecast_approved":False,
            "frame_st_is_not_course_st":True,
            "source_receipt":{"received_at":received.isoformat(),
                              "sha256":evidence["sha256"],"source":"third_party_waku10"}}
