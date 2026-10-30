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
    if cutoff>now+timedelta(minutes=22):
        candidates.append((cutoff,row["レースコード"]))
candidates.sort()
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
        if before=="ok" and (len((data.get("beforeinfo") or {}).get("racers",[]))!=6):
            raise ValueError("verified preview missing racers")
        verified_cards.append(code)
        if before=="ok":verified_previews.append(code)
        print(json.dumps({"outcome":"CARD_PASS","schedule_source":source,"race":code,"card_source":data["meta"]["source"],"preview_status":before},ensure_ascii=False))
    except (HTTPError,ValueError,TimeoutError,OSError) as exc:
        errors.append({"race":code,"error":str(exc)[:160],"http_status":getattr(exc,"code",None)})
if errors:
    print(json.dumps({"outcome":"PARTIAL_FAILURES","tried":errors},ensure_ascii=False))
if not verified_cards:
    print(json.dumps({"outcome":"FAIL","tried":errors},ensure_ascii=False))
    raise SystemExit("NO_LIVE_PREDEADLINE_RACECARD_VERIFIED")
print(json.dumps({"outcome":"PASS","card_verified_count":len(verified_cards),"preview_verified_count":len(verified_previews),"preview_not_yet_verified":len(verified_cards)-len(verified_previews),"failed":errors},ensure_ascii=False))
