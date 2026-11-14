"""Exercise live Render CLEAN racecard API against today's upstream holding races."""
import json
from datetime import datetime,timedelta
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from urllib.parse import urlencode
from zoneinfo import ZoneInfo
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from clean_direct_sources import holding_rows
from scripts.live_racecard_candidate_priority import (rank_candidates, t12_window_open,
    live_sampling_window_open, preview_codes_at_receipt, fresh_candidates_at_selection,
    verified_csv_pair_receipts)
JST=ZoneInfo("Asia/Tokyo")
now=datetime.now(JST)
hd=now.strftime("%Y%m%d")
# GitHub schedule dispatch can be delayed across Japan midnight. A run
# outside racing hours must not report tomorrow's unpublished CSV as an
# ordinary upstream outage or count as valid unattended T-12 coverage.
import os
if os.environ.get("GITHUB_EVENT_NAME")=="schedule" and not live_sampling_window_open(now):
    print(json.dumps({"outcome":"SCHEDULED_LIVE_SAMPLE_OUTSIDE_JST_RACING_WINDOW",
                      "run_at_jst":now.isoformat(),"race_day":hd,
                      "reason":"cron_dispatch_too_late_or_early"},ensure_ascii=False))
    raise SystemExit("NO_VALID_UNATTENDED_RACE_WINDOW")
try:
    rows,_,_=holding_rows(hd)
    source="boatcast_holding"
except (HTTPError,OSError,ValueError,TimeoutError):
    # Holding feed may deny GitHub runners with HTTP 403. Use the same
    # separately validated pre-race source available to the production API.
    from clean_openapi_sources import load
    rows,_,_,_,_=load(hd)
    source="nonofficial_openapi"
candidates=[]
for row in rows:
    cutoff=datetime.strptime(hd+row["電話投票締切予定"],"%Y%m%d%H:%M").replace(tzinfo=JST)
    if cutoff>now+timedelta(minutes=2):
        candidates.append((cutoff,row["レースコード"]))
candidates.sort()
# Prefer a currently published, race-matched predeadline exhibition over
# arbitrary earliest races; separately retain the ordinary racecard sample.
preview_candidates=set()
preview_source_status={}
preview_source_codes={}
try:
    from clean_racecard import _preview_rows
    path=f"{hd[:4]}/{hd[4:6]}/{hd[6:8]}.csv"
    for kind in ("tkz","stt"):
        try:
            preview_rows,digest=_preview_rows(kind,path)
            source_received_at=datetime.now(JST)
            selected=preview_codes_at_receipt(preview_rows,hd,source_received_at)
            preview_source_codes[kind]=selected
            preview_source_status[kind]="ok"
            print(json.dumps({"outcome":"PREVIEW_SOURCE_RECEIVED","kind":kind,
                              "source_received_at_jst":source_received_at.isoformat(),
                              "matched_future_count":len(selected),"sha256":digest},ensure_ascii=False))
        except (OSError,ValueError,KeyError,TimeoutError,HTTPError) as exc:
            preview_source_status[kind]=type(exc).__name__
            print(json.dumps({"outcome":"PREVIEW_SOURCE_UNAVAILABLE","kind":kind,
                              "reason":type(exc).__name__,"detail":str(exc)[:140]},ensure_ascii=False))
    preview_candidates=preview_source_codes.get("tkz",set()) & preview_source_codes.get("stt",set())
except ImportError as exc:
    print(json.dumps({"outcome":"PREVIEW_ADAPTER_IMPORT_UNAVAILABLE",
                      "reason":str(exc)[:140]},ensure_ascii=False))
# Recheck opportunity after the independent HTTP source probes. Stale
# scan-start time can promote a race whose T-12 window closed in transit.
selection_now=datetime.now(JST)
candidates,expired_during_source_probe=fresh_candidates_at_selection(candidates,selection_now)
candidates=rank_candidates(candidates,preview_candidates,selection_now)
t12_opportunities=sum(t12_window_open(deadline,selection_now) for deadline,code in candidates)
if expired_during_source_probe:
    print(json.dumps({"outcome":"RACECARD_CANDIDATES_EXPIRED_DURING_SOURCE_PROBE",
                      "selection_at_jst":selection_now.isoformat(),
                      "expired":[{"race":code,"deadline":deadline.isoformat()}
                                 for deadline,code in expired_during_source_probe]},ensure_ascii=False))
print(json.dumps({"outcome":"PREVIEW_CANDIDATES","eligible":len(preview_candidates),
                  "upcoming_candidates":len(candidates),"t12_opportunities":t12_opportunities,
                  "selection_at_jst":selection_now.isoformat(),
                  "preview_source_status":preview_source_status,
                  "expired_during_source_probe":len(expired_during_source_probe),
                  "sampled":[{"race":code,"deadline":deadline.isoformat(),
                              "t12_window_open":t12_window_open(deadline,selection_now),
                              "preview_candidate":code in preview_candidates}
                             for deadline,code in candidates[:3]]},ensure_ascii=False))
if not candidates:
    raise SystemExit("NO_ELIGIBLE_UPCOMING_RACES: need a real predeadline sample")
errors=[]
verified_cards=[]
verified_previews=[]
verified_t12=[]
for source_deadline,code in candidates[:3]:
    # Early enough at selection is only a *chance* to prove T-12. The
    # independent live API receipt and both source observations still decide.
    print(json.dumps({"outcome":"T12_SAMPLE_STARTED","race":code,
                      "deadline":source_deadline.isoformat(),
                      "t12_possible_at_selection":t12_window_open(source_deadline,selection_now)},ensure_ascii=False))
    url="https://boat-edge-clean.onrender.com/api/clean-racecard?"+urlencode({"hd":hd,"jcd":str(int(code[8:10])),"rno":str(int(code[10:12]))})
    try:
        with urlopen(Request(url,headers={"User-Agent":"CLEAN-E2E/1.0","Cache-Control":"no-cache"}),timeout=15) as res:
            data=json.load(res)
            if res.status!=200:raise ValueError("unexpected HTTP status")
        response_received_at=datetime.now(JST)
        if data.get("race_key")!=f"{hd}-{code[8:10]}-{code[10:12]}":
            raise ValueError("wrong race key")
        # Eligibility at candidate selection is insufficient if an HTTP request
        # completes after the race cutoff; never certify a post-cutoff response.
        deadline_text=data.get("meta",{}).get("deadline")
        if not isinstance(deadline_text,str):raise ValueError("race deadline missing")
        response_deadline=datetime.strptime(hd+deadline_text,"%Y%m%d%H:%M").replace(tzinfo=JST)
        if response_deadline!=source_deadline:raise ValueError("API deadline differs from independent race schedule")
        if datetime.now(JST)>=response_deadline:raise ValueError("race cutoff passed before response verification")
        if len(data.get("racers",[]))!=6:raise ValueError("missing racer rows")
        audit=data.get("source_audit",{})
        if audit.get("race_card",{}).get("status")!="ok":raise ValueError("unverified card source")
        before=audit.get("beforeinfo",{}).get("status")
        if before=="ok":
            preview=data.get("beforeinfo") or {}
            exhibitions=preview.get("racers") or []
            starts=preview.get("start_exhibition") or []
            if len(exhibitions)!=6 or len(starts)!=6:
                raise ValueError("verified preview missing six racers or starts")
            if sorted(entry.get("lane") for entry in exhibitions)!=list(range(1,7)):
                raise ValueError("verified preview missing six unique exhibition lanes")
            if sorted(entry.get("lane") for entry in starts)!=list(range(1,7)):
                raise ValueError("verified preview missing six unique starting lanes")
            if sorted(entry.get("course") for entry in starts)!=list(range(1,7)):
                raise ValueError("verified preview course permutation invalid")
            for entry in exhibitions:
                if not isinstance(entry.get("exhibition_time"),(int,float)) or not 5<=entry["exhibition_time"]<=9:
                    raise ValueError("verified exhibition time invalid")
                if not isinstance(entry.get("tilt"),(int,float)) or not -1<=entry["tilt"]<=3:
                    raise ValueError("verified tilt invalid")
            from datetime import datetime as _datetime
            fetched=_datetime.fromisoformat(audit["beforeinfo"]["fetched_at"])
            deadline=_datetime.strptime(hd+data["meta"]["deadline"],"%Y%m%d%H:%M").replace(tzinfo=JST)
            if fetched.tzinfo is None or fetched>=deadline or fetched>datetime.now(JST):
                raise ValueError("verified exhibition not predeadline")
            # Official beforeinfo can independently prove the six exhibition
            # values, without proving the two separate tkz/stt CSV receipts
            # needed for the strict research T-12 pair. Never elevate an
            # official-only receipt into a two-source T-12 success.
            source_times,source_issues=verified_csv_pair_receipts(
                audit["beforeinfo"],deadline,response_received_at)
            if source_issues:
                print(json.dumps({"outcome":"T12_PAIR_NOT_VERIFIED","race":code,
                                  "reason":"independent_csv_source_pair_incomplete",
                                  "beforeinfo_source":audit["beforeinfo"].get("source"),
                                  "source_issues":source_issues,
                                  "formal":False},ensure_ascii=False))
            else:
                t12_limit=deadline-timedelta(minutes=12)
                t12_checks={"api_received_by_t12":response_received_at<=t12_limit,
                            "tkz_observed_by_t12":source_times["tkz"]<=t12_limit,
                            "stt_observed_by_t12":source_times["stt"]<=t12_limit}
                if all(t12_checks.values()):
                    verified_t12.append(code)
                    print(json.dumps({"outcome":"T12_COMPLETE_PAIR_PASS","race":code,
                                      "observed_by":t12_limit.isoformat(),"response_received_at":response_received_at.isoformat(),
                                      "source_observed_at":{kind:v.isoformat() for kind,v in source_times.items()}},ensure_ascii=False))
                else:
                    print(json.dumps({"outcome":"T12_PAIR_NOT_VERIFIED","race":code,
                                      "limit":t12_limit.isoformat(),"checks":t12_checks,
                                      "response_received_at":response_received_at.isoformat(),
                                      "source_observed_at":{kind:v.isoformat() for kind,v in source_times.items()}},ensure_ascii=False))
            print(json.dumps({"outcome":"EXHIBITION_PASS","race":code,"courses":[entry["course"] for entry in starts],"source":audit["beforeinfo"].get("source")},ensure_ascii=False))
        verified_cards.append(code)
        if before=="ok":verified_previews.append(code)
        print(json.dumps({"outcome":"CARD_PASS","schedule_source":source,"race":code,"card_source":data["meta"]["source"],"preview_status":before,"preview_source_status":audit.get("beforeinfo",{}).get("source_status")},ensure_ascii=False))
    except (HTTPError,ValueError,TimeoutError,OSError) as exc:
        errors.append({"race":code,"error":str(exc)[:160],"http_status":getattr(exc,"code",None)})
if errors:
    print(json.dumps({"outcome":"PARTIAL_FAILURES","tried":errors},ensure_ascii=False))
if not verified_cards:
    print(json.dumps({"outcome":"FAIL","tried":errors},ensure_ascii=False))
    raise SystemExit("NO_LIVE_PREDEADLINE_RACECARD_VERIFIED")
if not verified_previews:
    print(json.dumps({"outcome":"PREDEADLINE_EXHIBITION_NOT_VERIFIED","card_verified_count":len(verified_cards),"preview_verified_count":0,"failed":errors},ensure_ascii=False))
    raise SystemExit("NO_SIX_BOAT_PREDEADLINE_EXHIBITION_VERIFIED")
if not verified_t12:
    print(json.dumps({"outcome":"T12_UNVERIFIED","card_verified_count":len(verified_cards),"preview_verified_count":len(verified_previews),"failed":errors},ensure_ascii=False))
    raise SystemExit("NO_T12_SIX_BOAT_PAIR_VERIFIED")
print(json.dumps({"outcome":"PASS","card_verified_count":len(verified_cards),"preview_verified_count":len(verified_previews),"t12_verified_count":len(verified_t12),"preview_not_yet_verified":len(verified_cards)-len(verified_previews),"failed":errors},ensure_ascii=False))
