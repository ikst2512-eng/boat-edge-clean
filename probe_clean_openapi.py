"""Read-only availability probe for nonofficial Boatrace Open API pre-race fields.

Never writes a prediction, does not use results/previews, and never certifies a forecast.
"""
import json
import re
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

JST=timezone(timedelta(hours=9))
BASE="https://boatraceopenapi.github.io/api/v1/"
LIMIT=4_000_000

def check(day, fetch=None):
    if not re.fullmatch(r"20\d{6}",day):
        raise ValueError("invalid_day")
    datetime.strptime(day,"%Y%m%d")
    url=f"{BASE}{day[:4]}/{day}.json"
    if fetch is None:
        def fetch(target):
            with urlopen(Request(target,headers={"User-Agent":"BOAT-EDGE-CLEAN/1.0"}),timeout=12) as response:
                raw=response.read(LIMIT+1)
                if len(raw)>LIMIT:raise ValueError("source_too_large")
                return raw
    try:
        raw=fetch(url)
        if len(raw)>LIMIT:raise ValueError("source_too_large")
        data=json.loads(raw)
        stadiums=data.get("programs",{}).get("stadiums",{})
        if not isinstance(stadiums,dict):raise ValueError("invalid_stadiums")
        eligible=0
        incomplete=0
        earliest=None
        for venue_key,venue in stadiums.items():
            if not isinstance(venue,dict):continue
            races=venue.get("races",{})
            if not isinstance(races,dict):continue
            for race_key,race in races.items():
                if not isinstance(race,dict):continue
                try:
                    if not (1<=int(venue_key)<=24 and 1<=int(race_key)<=12):continue
                    if race.get("date")!=f"{day[:4]}-{day[4:6]}-{day[6:8]}":continue
                    deadline=datetime.strptime(race["closed_at"],"%Y-%m-%d %H:%M:%S").replace(tzinfo=JST)
                    racers=race["racers"]
                    if not isinstance(racers,dict) or set(map(str,racers))!=set("123456"):raise ValueError("six_lanes")
                    registrations=[]
                    for lane in range(1,7):
                        racer=racers[str(lane)]
                        if int(racer["entry_number"])!=lane:raise ValueError("lane")
                        registration=str(racer["number"])
                        rate=float(racer["national_win_rate"])
                        if not re.fullmatch(r"\d{4}",registration) or not 0<rate<20:raise ValueError("invalid_racer")
                        registrations.append(registration)
                    if len(set(registrations))!=6:raise ValueError("duplicate_registration")
                    eligible+=1
                    if earliest is None or deadline<earliest:earliest=deadline
                except (KeyError,TypeError,ValueError,OverflowError):
                    incomplete+=1
        return {"status":"available","source":"nonofficial_openapi_v1","day_jst":day,
                "eligible_six_boat_races":eligible,"incomplete_races":incomplete,
                "earliest_deadline_jst":earliest.isoformat() if earliest else None,
                "forecast_written":False}
    except HTTPError as exc:
        return {"status":"not_published" if exc.code==404 else "http_error",
                "http_status":exc.code,"day_jst":day,"forecast_written":False}
    except (URLError,TimeoutError,OSError,ValueError,UnicodeError,json.JSONDecodeError) as exc:
        return {"status":"unavailable","error_type":type(exc).__name__,"day_jst":day,"forecast_written":False}

if __name__=="__main__":
    print(json.dumps(check(datetime.now(JST).strftime("%Y%m%d")),ensure_ascii=False))
