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
JST=ZoneInfo("Asia/Tokyo")
now=datetime.now(JST)
hd=now.strftime("%Y%m%d")
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
try:
    from clean_racecard import _preview_rows
    path=f"{hd[:4]}/{hd[4:6]}/{hd[6:8]}.csv"
    matched={}
    for kind in ("tkz","stt"):
        preview_rows,_=_preview_rows(kind,path)
        selected=set()
        for row in preview_rows:
            try:
                code=row["レースコード"]
                observed=datetime.fromisoformat(row["取得日時"])
                cutoff=datetime.strptime(hd+row["締切時刻"],"%Y%m%d%H:%M").replace(tzinfo=JST)
                if observed.tzinfo and observed<=datetime.now(JST) and observed<cutoff and datetime.now(JST)<cutoff:
                    selected.add(code)
            except (ValueError,KeyError,TypeError):
                continue
        matched[kind]=selected
    preview_candidates=matched["tkz"] & matched["stt"]
except (OSError,ValueError,KeyError,TimeoutError):
    pass
candidates.sort(key=lambda item:(item[1] not in preview_candidates,item[0]))
print(json.dumps({"outcome":"PREVIEW_CANDIDATES","eligible":len(preview_candidates)},ensure_ascii=False))
if not candidates:
    raise SystemExit("NO_ELIGIBLE_UPCOMING_RACES: need a real predeadline sample")
errors=[]
verified_cards=[]
verified_previews=[]
for _,code in candidates[:3]:
    url="https://boat-edge-clean.onrender.com/api/clean-racecard?"+urlencode({"hd":hd,"jcd":str(int(code[8:10])),"rno":str(int(code[10:12]))})
    try:
        with urlopen(Request(url,headers={"User-Agent":"CLEAN-E2E/1.0","Cache-Control":"no-cache"}),timeout=15) as res:
            data=json.load(res)
            if res.status!=200:raise ValueError("unexpected HTTP status")
        if data.get("race_key")!=f"{hd}-{code[8:10]}-{code[10:12]}":
            raise ValueError("wrong race key")
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
            if fetched.tzinfo is None or fetched>=deadline:
                raise ValueError("verified exhibition not predeadline")
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
print(json.dumps({"outcome":"PASS","card_verified_count":len(verified_cards),"preview_verified_count":len(verified_previews),"preview_not_yet_verified":len(verified_cards)-len(verified_previews),"failed":errors},ensure_ascii=False))
