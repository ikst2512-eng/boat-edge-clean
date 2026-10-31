"""Independent CLEAN pre-race card adapter from documented public BoatraceCSV fields."""
from datetime import datetime
from urllib.error import HTTPError,URLError
import re
import csv
import io
import hashlib
from urllib.request import Request,urlopen
from concurrent.futures import ThreadPoolExecutor
from research_model import BASE,JST,read_rows


def _num(v):
    try:
        return float(v) if v not in (None,"","-") else None
    except (ValueError,TypeError):
        return None



def _preview_rows(kind,path):
    url="https://boatracecsv.github.io/data/previews/"+kind+"/"+path
    with urlopen(Request(url,headers={"User-Agent":"BOAT-EDGE-CLEAN/1.0"}),timeout=8) as response:
        if response.status!=200:raise ValueError("preview_unavailable")
        raw=response.read(2_000_001)
        if len(raw)>2_000_000:raise ValueError("preview_too_large")
    return list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))),hashlib.sha256(raw).hexdigest()


def _fetch_preview(code,path,deadline):
    """Only use race-matched and independently time-stamped predeadline data."""
    # Concurrent independent source reads keep server response bounded when
    # one published preview CSV is unavailable or slow.
    observed_now=datetime.now(JST)
    def select(kind):
        try:
            rows,sha=_preview_rows(kind,path)
        except (OSError,ValueError,KeyError,UnicodeError):
            return kind,None,"source_unavailable"
        candidates=[]
        matching=0
        incomplete=0
        for row in rows:
            if row.get("レースコード")!=code:continue
            matching+=1
            if row.get("締切時刻")!=deadline.strftime("%H:%M"):continue
            try:
                observed=datetime.fromisoformat(row.get("取得日時",""))
            except (ValueError,TypeError):
                continue
            if observed.tzinfo is not None and observed<=observed_now and observed<deadline:
                # A newer partial snapshot must not hide earlier, complete,
                # independently time-stamped measurements for this same race.
                if kind=="tkz":
                    complete=all(
                        (_num(row.get(f"艇{i}_展示タイム")) is not None and
                         5<=_num(row.get(f"艇{i}_展示タイム"))<=9 and
                         _num(row.get(f"艇{i}_チルト")) is not None and
                         -1<=_num(row.get(f"艇{i}_チルト"))<=3)
                        for i in range(1,7))
                elif kind=="stt":
                    course=[_num(row.get(f"艇{i}_コース")) for i in range(1,7)]
                    complete=(all(v is not None for v in course) and
                        sorted(course)==[1.,2.,3.,4.,5.,6.] and
                        all(re.fullmatch(r"(?:[+-]?(?:\d+(?:\.\d+)?|\.\d+)|F\.?\d{1,2})",
                            str(row.get(f"艇{i}_スタート展示") or "").strip()) for i in range(1,7)))
                else:
                    complete=True
                if complete:candidates.append((observed,row))
                else:incomplete+=1
        if candidates:
            observed,row=max(candidates,key=lambda x:x[0])
            return kind,(observed,row,sha),"ok"
        return kind,None,("race_not_published" if not matching else "incomplete_exhibition" if incomplete else "deadline_or_timestamp_unverified")
    with ThreadPoolExecutor(max_workers=3) as pool:
        found=list(pool.map(select,("tkz","stt","sui")))
    sources={kind:value for kind,value,state in found if value is not None}
    availability={kind:state for kind,value,state in found}
    if "tkz" not in sources or "stt" not in sources:
        status=("invalid_or_incomplete_exhibition" if any(availability.get(k)=="incomplete_exhibition" for k in ("tkz","stt")) else "not_published_or_unavailable")
        return None,{"status":status,"source_status":availability}
    racers=[];starts=[]
    tkz=sources["tkz"][1];stt=sources["stt"][1]
    for lane in range(1,7):
        prefix=f"艇{lane}_"
        racers.append({"lane":lane,"exhibition_time":_num(tkz.get(prefix+"展示タイム")),"tilt":_num(tkz.get(prefix+"チルト"))})
        starts.append({"lane":lane,"course":_num(stt.get(prefix+"コース")),"st":stt.get(prefix+"スタート展示") or None})
    # A CSV row and a timestamp alone do not prove valid exhibition measurements.
    # Only publish a complete six-boat set; otherwise keep the card and fail closed.
    times=[r["exhibition_time"] for r in racers]
    tilts=[r["tilt"] for r in racers]
    courses=[r["course"] for r in starts]
    # A blank start-exhibition ST is incomplete evidence, even if course is known.
    start_times=[r["st"] for r in starts]
    if (any(v is None or re.fullmatch(r"(?:[+-]?(?:\d+(?:\.\d+)?|\.\d+)|F\.?\d{1,2})", str(v).strip()) is None for v in start_times)
        or any(v is None or not 5.0<=v<=9.0 for v in times)
        or any(v is None or not -1.0<=v<=3.0 for v in tilts)
        or any(v is None for v in courses)
        or sorted(courses)!=[1.,2.,3.,4.,5.,6.]):
        return None,{"status":"invalid_or_incomplete_exhibition","source_status":availability}
    audit={"status":"ok","source_status":availability,"fetched_at":max(sources["tkz"][0],sources["stt"][0]).isoformat(),
           "source":"BoatraceCSV predeadline snapshots",
           "sources":{k:{"observed_at":v[0].isoformat(),"sha256":v[2]} for k,v in sources.items()}}
    preview={"racers":racers,"start_exhibition":starts}
    if "sui" in sources:
        row=sources["sui"][1]
        preview["weather"]={k:row.get(k) for k in ("風速(m)","風向","波の高さ(cm)","天候","気温(℃)","水温(℃)")}
    return preview,audit


def racecard(hd,jcd,rno):
    if not re.fullmatch(r"20\d{6}",str(hd)) or not re.fullmatch(r"(?:0?[1-9]|1[0-9]|2[0-4])",str(jcd)) or not re.fullmatch(r"[1-9]|1[0-2]",str(rno)):
        raise ValueError("invalid_race_key")
    datetime.strptime(hd,"%Y%m%d")
    code=f"{hd}{int(jcd):02d}{int(rno):02d}"
    historical=datetime.strptime(hd,"%Y%m%d").date()<datetime.now(JST).date()
    path=f"{hd[:4]}/{hd[4:6]}/{hd[6:8]}.csv"
    # Daily generated CSV can be absent before racing closes. Read primary first,
    # then obtain exactly this race from the independent documented live origin.
    from clean_direct_sources import holding_rows,fetch_bytes,parse_card,ROOT
    source="CLEAN_PUBLIC_PRE_RACE_CSV"
    openapi_cards=None
    def alternate_program():
        nonlocal openapi_cards
        from clean_openapi_sources import load
        alt_titles,openapi_cards,alt_time,alt_sha,_=load(hd)
        return alt_titles,alt_time,alt_sha
    try:
        titles,title_fetched,title_sha=read_rows(BASE+"title/"+path)
    except (HTTPError,URLError,TimeoutError,OSError,ValueError,UnicodeError):
        try:
            titles,title_fetched,title_sha=holding_rows(hd)
            source="CLEAN_DIRECT_PRE_RACE"
        except (HTTPError,URLError,TimeoutError,OSError,ValueError,UnicodeError):
            titles,title_fetched,title_sha=alternate_program()
            source="CLEAN_NONOFFICIAL_OPENAPI_PRE_RACE"
    title=[row for row in titles if row.get("レースコード")==code]
    if not title and source=="CLEAN_PUBLIC_PRE_RACE_CSV":
        # A published daily file can precede this race's publication.
        # Try the race-specific live source before reporting a missing card.
        try:
            titles,title_fetched,title_sha=holding_rows(hd)
            source="CLEAN_DIRECT_PRE_RACE"
            title=[row for row in titles if row.get("レースコード")==code]
        except (HTTPError,URLError,TimeoutError,OSError,ValueError,UnicodeError):
            pass
    if not title and source!="CLEAN_NONOFFICIAL_OPENAPI_PRE_RACE":
        alt_titles,alt_fetched,alt_sha=alternate_program()
        alt_match=[row for row in alt_titles if row.get("レースコード")==code]
        if len(alt_match)==1:
            title=alt_match
            title_fetched,title_sha=alt_fetched,alt_sha
            source="CLEAN_NONOFFICIAL_OPENAPI_PRE_RACE"
    if len(title)!=1:
        # A missing race must not be confused with a source fetch failure.
        # Keep the public error stable while preserving race-level diagnostics.
        import logging
        logging.info("racecard_title_missing race=%s source=%s title_rows=%s", code, source, len(titles))
        raise ValueError("race_card_not_available")
    meta=title[0]
    deadline_text=meta.get("電話投票締切予定","")
    if not re.fullmatch(r"(?:[01][0-9]|2[0-3]):[0-5][0-9]",deadline_text):
        raise ValueError("deadline_not_available")
    deadline=datetime.strptime(hd+deadline_text,"%Y%m%d%H:%M").replace(tzinfo=JST)
    if title_fetched>=deadline and not historical:raise ValueError("race_already_closed")
    try:
        cards,card_fetched,card_sha=read_rows(BASE+"race_cards/"+path)
        card=[row for row in cards if row.get("レースコード")==code]
        if len(card)!=1:raise ValueError("race_card_not_available")
        fields=card[0]
    except (HTTPError,URLError,TimeoutError,OSError,ValueError,UnicodeError) as exc:
        # Never silently replace malformed/suspicious source evidence; only
        # fall back on unavailable daily source, not a wrong-race CSV.
        if isinstance(exc,ValueError) and str(exc) not in ("race_card_not_available","source unavailable"):
            raise
        url=f"{ROOT}/hp_txt/{int(jcd):02d}/bc_j_str3_{hd}_{int(jcd):02d}_{int(rno):02d}.txt"
        try:
            raw=fetch_bytes(url)
            fields=parse_card(raw,code)
            card_fetched=datetime.now(JST)
            card_sha=hashlib.sha256(raw).hexdigest()
            source="CLEAN_DIRECT_PRE_RACE"
        except (HTTPError,URLError,TimeoutError,OSError,ValueError,UnicodeError):
            if openapi_cards is None:
                _,card_fetched,card_sha=alternate_program()
            else:
                card_fetched=title_fetched
                card_sha=title_sha
            matches=[item for item in openapi_cards if item.get("レースコード")==code]
            if len(matches)!=1:raise ValueError("race_card_not_available")
            fields=matches[0]
            source="CLEAN_NONOFFICIAL_OPENAPI_PRE_RACE"
    if card_fetched>=deadline and not historical:raise ValueError("race_already_closed")
    racers=[]
    seen_registrations=set()
    for i in range(1,7):
        p=f"艇{i}_"
        number=str(fields.get(p+"登録番号","")).strip()
        if not re.fullmatch(r"\d{4}",number):raise ValueError("six_racers_unavailable")
        if number in seen_registrations:raise ValueError("duplicate_registration")
        seen_registrations.add(number)
        racers.append({
          "lane":i,"registration_no":number,
          "name":fields.get(p+"選手名") or "未提供",
          "class":fields.get(p+"級別") or "—",
          "avg_st":_num(fields.get(p+"全国平均ST")),
          "F":_num(fields.get(p+"F本数")),"L":_num(fields.get(p+"L本数")),
          "national":{"win_rate":_num(fields.get(p+"全国勝率")),"quinella_rate":_num(fields.get(p+"全国2連対率")),"trio_rate":_num(fields.get(p+"全国3連対率"))},
          "local":{"win_rate":_num(fields.get(p+"当地勝率")),"quinella_rate":_num(fields.get(p+"当地2連対率")),"trio_rate":_num(fields.get(p+"当地3連対率"))},
          "motor":{"no":_num(fields.get(p+"モーター番号")),"quinella_rate":_num(fields.get(p+"モーター2連対率")),"trio_rate":_num(fields.get(p+"モーター3連対率"))},
          "boat":{"no":_num(fields.get(p+"ボート番号")),"quinella_rate":_num(fields.get(p+"ボート2連対率")),"trio_rate":_num(fields.get(p+"ボート3連対率"))}})
    beforeinfo,before_audit=(None,{"status":"not_verified_historical"}) if historical else _fetch_preview(code,path,deadline)
    return {"schema_version":"boat-edge-race-v5","race_key":f"{hd}-{int(jcd):02d}-{int(rno):02d}",
       "meta":{"date":f"{hd[:4]}-{hd[4:6]}-{hd[6:8]}","venue_code":f"{int(jcd):02d}","race_no":int(rno),
         "deadline":deadline_text,"phase":"HISTORICAL_READ_ONLY" if historical else "PRE_RESULT","results_seen":False,"unlock":False,"scoring":False,
         "source":source,"historical_reference_only":historical},
       "source_audit":{"race_card":{"status":"ok","fetched_at":card_fetched.isoformat(),"sha256":card_sha,"predeadline_verified":not historical and card_fetched<deadline},
         "beforeinfo":before_audit},
       "racers":racers,"beforeinfo":beforeinfo}
