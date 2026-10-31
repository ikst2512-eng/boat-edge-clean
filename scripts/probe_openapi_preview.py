"""Read-only nonofficial pre-race preview inspection; no prediction use or backfill."""
import hashlib, json, math, re
from datetime import datetime, timedelta
from urllib.request import Request, urlopen
from research_model import JST

BASE="https://boatraceopenapi.github.io/api/v1/"
def probe(day, venue, race, fetch=None, now=None):
    if not re.fullmatch(r"20[0-9]{6}",day): raise ValueError("invalid date")
    datetime.strptime(day,"%Y%m%d")
    if not (1<=venue<=24 and 1<=race<=12): raise ValueError("invalid race key")
    now=now or datetime.now(JST)
    url=f"{BASE}{day[:4]}/{day}.json"
    if fetch is None:
        def fetch(target):
            with urlopen(Request(target,headers={"User-Agent":"BOAT-EDGE-CLEAN-RESEARCH/1.0"}),timeout=10) as response:
                raw=response.read(4_000_001)
                if len(raw)>4_000_000: raise ValueError("source too large")
                return raw
    raw=fetch(url)
    if not isinstance(raw,bytes) or not raw or len(raw)>4_000_000: raise ValueError("invalid source")
    data=json.loads(raw)
    r=data["programs"]["stadiums"][str(venue)]["races"][str(race)]
    deadline=datetime.strptime(r["closed_at"],"%Y-%m-%d %H:%M:%S").replace(tzinfo=JST)
    preview=r.get("preview")
    outcome={"race_code":f"{day}{venue:02d}{race:02d}","url":url,"received_at_jst":now.isoformat(),
             "source_sha256":hashlib.sha256(raw).hexdigest(),"deadline_jst":deadline.isoformat(),
             "predeadline":now<deadline-timedelta(minutes=12),"preview_available":bool(preview),
             "source":"nonofficial_openapi_v1","source_freshness_unverified":True,
             "six_boats_verified":False}
    if not isinstance(preview,dict) or not outcome["predeadline"]: return outcome
    racers=preview.get("racers")
    if not isinstance(racers,dict) or set(racers)!=set("123456"):return outcome
    boats=[]
    for i in range(1,7):
        p=racers[str(i)]
        if p.get("entry_number")!=i: return outcome
        course=p.get("course_number")
        timing=p.get("start_timing")
        exhibition=p.get("exhibition_time")
        tilt=p.get("tilt_adjustment")
        if not (isinstance(course,int) and 1<=course<=6 and
                all(type(v) in (float,int) and math.isfinite(v) for v in (timing,exhibition,tilt)) and
                -1<=timing<=2 and 5<exhibition<10 and -2<=tilt<=3):
            return outcome
        boats.append({"lane":i,"course":course,"exhibition_st":timing,"exhibition_time":exhibition,"tilt":tilt})
    if len({b["course"] for b in boats})!=6:return outcome
    outcome["six_boats_verified"]=True
    outcome["boats"]=boats
    return outcome
