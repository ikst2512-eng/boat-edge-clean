"""Bounded direct pre-race source fallback, independent of legacy repository.

Boatcast's holding list and per-race bc_j_str3 TSV are the documented upstream
of the daily CSVs. Never read results or retroactively generate forecasts.
"""
import hashlib
import json
import re
from datetime import datetime, timedelta
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from research_model import JST

ROOT="https://race.boatcast.jp"
HEADERS={"User-Agent":"BOAT-EDGE-CLEAN/1.0","Accept":"application/json,text/plain,*/*"}
MAX_RACES_PER_RUN=18


def fetch_bytes(url,limit=2_000_000):
    if not url.startswith(ROOT+"/"):raise ValueError("source_not_allowlisted")
    with urlopen(Request(url,headers=HEADERS),timeout=8) as res:
        if res.status!=200:raise ValueError("upstream_http_status")
        raw=res.read(limit+1)
        if len(raw)>limit:raise ValueError("upstream_too_large")
        return raw


def holding_rows(day,fetch=fetch_bytes):
    if not re.fullmatch(r"20[0-9]{6}",day):raise ValueError("day_invalid")
    url=f"{ROOT}/api_txt/getHoldingList2_{day}.json"
    raw=fetch(url)
    data=json.loads(raw)
    if not isinstance(data,dict) or data.get("res_cd")!=0 or not isinstance(data.get("return_info"),list):
        raise ValueError("holding_list_invalid")
    rows=[]
    seen=set()
    for venue in data["return_info"]:
        if not isinstance(venue,dict):continue
        try:jo=int(venue.get("RaceStudiumNo"))
        except (TypeError,ValueError):continue
        if not 1<=jo<=24:continue
        titles=venue.get("RaceTitleAll") or []
        deadlines=venue.get("DeadlineTimeAll") or []
        cancels=venue.get("CancelStatusAll") or []
        if not isinstance(titles,list) or not isinstance(deadlines,list):continue
        for idx in range(min(12,len(titles),len(deadlines))):
            clock=str(deadlines[idx]).strip()
            if not re.fullmatch(r"(?:[01][0-9]|2[0-3]):?[0-5][0-9]",clock):continue
            clock=clock.replace(":","")
            if isinstance(cancels,list) and idx<len(cancels) and str(cancels[idx]).strip():continue
            code=f"{day}{jo:02d}{idx+1:02d}"
            if code in seen:raise ValueError("duplicate_holding_race")
            seen.add(code)
            rows.append({"レースコード":code,"電話投票締切予定":clock[:2]+":"+clock[2:],
                "レース名":str(titles[idx]).strip()})
    if not rows:raise ValueError("no_upcoming_schedule")
    return rows,datetime.now(JST),hashlib.sha256(raw).hexdigest()


def parse_card(raw,code):
    text=raw.decode("utf-8-sig")
    lines=text.splitlines()
    if len(lines)<8 or not lines[0].startswith("data=") or lines[1].split("\t")[0].strip()!="1":
        raise ValueError("race_card_unavailable")
    row={"レースコード":code}
    seen=set()
    for lane,line in enumerate(lines[2:8],1):
        c=line.split("\t")
        if len(c)<25:raise ValueError("incomplete_race_card")
        number=c[0].strip()
        if not re.fullmatch(r"[0-9]{4}",number) or number in seen:
            raise ValueError("duplicate_or_missing_registration")
        seen.add(number)
        p=f"艇{lane}_"
        keys={"登録番号":0,"選手名":1,"級別":5,"全国平均ST":9,
              "全国勝率":10,"全国2連対率":11,"全国3連対率":12,
              "当地勝率":13,"当地2連対率":14,"当地3連対率":15,
              "モーター番号":17,"モーター2連対率":18,"モーター3連対率":19,
              "ボート番号":21,"ボート2連対率":22,"ボート3連対率":23}
        for name,index in keys.items():row[p+name]=c[index].strip()
        row[p+"F本数"]=str(0 if not c[7].strip() else int(c[7].strip().removeprefix("F") or "1"))
        row[p+"L本数"]=str(0 if not c[8].strip() else int(c[8].strip().removeprefix("L") or "1"))
        rate=float(row[p+"全国勝率"])
        if not 0<rate<20:raise ValueError("national_rate_invalid")
    return row


def direct_cards(day,titles,existing_codes=(),now=None,fetch=fetch_bytes,limit=MAX_RACES_PER_RUN):
    now=now or datetime.now(JST)
    existing=set(existing_codes)
    pending=[]
    for title in titles:
        code=title["レースコード"]
        if code in existing:continue
        cutoff=datetime.strptime(day+title["電話投票締切予定"],"%Y%m%d%H:%M").replace(tzinfo=JST)
        if now+timedelta(minutes=20)<cutoff:pending.append((cutoff,code))
    pending.sort()
    cards=[]
    source_hashes={}
    failed={}
    for _,code in pending[:limit]:
        jo,rr=code[8:10],code[10:12]
        url=f"{ROOT}/hp_txt/{jo}/bc_j_str3_{day}_{jo}_{rr}.txt"
        try:
            raw=fetch(url)
            cards.append(parse_card(raw,code))
            source_hashes[code]=hashlib.sha256(raw).hexdigest()
        except (HTTPError,URLError,TimeoutError,OSError,ValueError,UnicodeError) as exc:
            key=type(exc).__name__
            failed[key]=failed.get(key,0)+1
    if not cards:return [],now,"",source_hashes,failed
    combined=hashlib.sha256("".join(source_hashes[c] for c in sorted(source_hashes)).encode("ascii")).hexdigest()
    return cards,now,combined,source_hashes,failed
