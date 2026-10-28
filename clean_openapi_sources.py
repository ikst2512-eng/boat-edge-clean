"""Bounded, strictly pre-race-only alternate CLEAN source.

Nonofficial API; do not read preview/results or certify source as official.
"""
import hashlib
import json
import re
from datetime import datetime
from urllib.request import Request, urlopen
from research_model import JST

BASE="https://boatraceopenapi.github.io/api/v1/"
MAX_BYTES=4_000_000

def load(day,fetch=None,now=None):
    if not re.fullmatch(r"20\d{6}",day):raise ValueError("invalid_day")
    datetime.strptime(day,"%Y%m%d")
    now=now or datetime.now(JST)
    url=f"{BASE}{day[:4]}/{day}.json"
    if fetch is None:
        def fetch(target):
            with urlopen(Request(target,headers={"User-Agent":"BOAT-EDGE-CLEAN/1.0"}),timeout=12) as response:
                return response.read(MAX_BYTES+1)
    raw=fetch(url)
    if len(raw)>MAX_BYTES:raise ValueError("source_too_large")
    digest=hashlib.sha256(raw).hexdigest()
    stadiums=json.loads(raw)["programs"]["stadiums"]
    if not isinstance(stadiums,dict):raise ValueError("stadiums_invalid")
    titles=[];cards=[];rejected=0;seen=set()
    for venue,entry in stadiums.items():
        if not isinstance(entry,dict) or not isinstance(entry.get("races"),dict):continue
        for race_no,race in entry["races"].items():
            try:
                code=f"{day}{int(venue):02d}{int(race_no):02d}"
                if not 1<=int(venue)<=24 or not 1<=int(race_no)<=12 or code in seen:raise ValueError("race_key")
                seen.add(code)
                if race["date"]!=f"{day[:4]}-{day[4:6]}-{day[6:8]}":raise ValueError("date_mismatch")
                deadline=datetime.strptime(race["closed_at"],"%Y-%m-%d %H:%M:%S").replace(tzinfo=JST)
                if deadline.strftime("%Y%m%d")!=day:raise ValueError("deadline_date")
                racers=race["racers"]
                if not isinstance(racers,dict) or set(racers)!=set("123456"):raise ValueError("lanes_incomplete")
                card={"レースコード":code}
                registrations=set()
                for i in range(1,7):
                    racer=racers[str(i)]
                    number=str(racer["number"])
                    rate=float(racer["national_win_rate"])
                    if int(racer["entry_number"])!=i or not re.fullmatch(r"\d{4}",number) or number in registrations or not 0<rate<20:
                        raise ValueError("invalid_racer")
                    registrations.add(number)
                    card[f"艇{i}_登録番号"]=number
                    card[f"艇{i}_全国勝率"]=str(rate)
                titles.append({"レースコード":code,"電話投票締切予定":deadline.strftime("%H:%M"),"レース名":str(race.get("title") or "")})
                cards.append(card)
            except (ValueError,KeyError,TypeError,AttributeError,OverflowError):
                rejected+=1
    if not titles:raise ValueError("no_valid_races")
    return titles,cards,now,digest,{"source":"nonofficial_openapi_v1","url":url,"valid":len(titles),"rejected":rejected}
