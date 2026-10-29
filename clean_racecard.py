"""Independent CLEAN pre-race card adapter from documented public BoatraceCSV fields."""
from datetime import datetime
import re
import csv
import io
import hashlib
from urllib.request import Request,urlopen
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
    sources={}
    for kind in ("tkz","stt","sui"):
        try:
            rows,sha=_preview_rows(kind,path)
            candidates=[]
            for row in rows:
                if row.get("レースコード")!=code or row.get("締切時刻")!=deadline.strftime("%H:%M"):continue
                observed=datetime.fromisoformat(row.get("取得日時",""))
                if observed.tzinfo is not None and observed<deadline:
                    candidates.append((observed,row))
            if candidates:
                observed,row=max(candidates,key=lambda x:x[0])
                sources[kind]=(observed,row,sha)
        except (OSError,ValueError,KeyError,UnicodeError):
            continue
    if "tkz" not in sources or "stt" not in sources:
        return None,{"status":"not_published_or_unavailable"}
    racers=[];starts=[]
    tkz=sources["tkz"][1];stt=sources["stt"][1]
    for lane in range(1,7):
        prefix=f"艇{lane}_"
        racers.append({"lane":lane,"exhibition_time":_num(tkz.get(prefix+"展示タイム")),"tilt":_num(tkz.get(prefix+"チルト"))})
        starts.append({"lane":lane,"course":_num(stt.get(prefix+"コース")),"st":stt.get(prefix+"スタート展示") or None})
    audit={"status":"ok","fetched_at":max(sources["tkz"][0],sources["stt"][0]).isoformat(),
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
    path=f"{hd[:4]}/{hd[4:6]}/{hd[6:8]}.csv"
    titles,title_fetched,title_sha=read_rows(BASE+"title/"+path)
    cards,card_fetched,card_sha=read_rows(BASE+"race_cards/"+path)
    title=[r for r in titles if r.get("レースコード")==code]
    card=[r for r in cards if r.get("レースコード")==code]
    if len(title)!=1 or len(card)!=1:raise ValueError("race_card_not_available")
    meta=title[0]; fields=card[0]
    deadline_text=meta.get("電話投票締切予定","")
    if not re.fullmatch(r"[0-2][0-9]:[0-5][0-9]",deadline_text):
        raise ValueError("deadline_not_available")
    deadline=datetime.strptime(hd+deadline_text,"%Y%m%d%H:%M").replace(tzinfo=JST)
    if max(title_fetched,card_fetched)>=deadline:raise ValueError("race_already_closed")
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
    beforeinfo,before_audit=_fetch_preview(code,path,deadline)
    return {"schema_version":"boat-edge-race-v5","race_key":f"{hd}-{int(jcd):02d}-{int(rno):02d}",
       "meta":{"date":f"{hd[:4]}-{hd[4:6]}-{hd[6:8]}","venue_code":f"{int(jcd):02d}","race_no":int(rno),
         "deadline":deadline_text,"phase":"PRE_RESULT","results_seen":False,"unlock":False,"scoring":False,
         "source":"CLEAN_PUBLIC_PRE_RACE_CSV"},
       "source_audit":{"race_card":{"status":"ok","fetched_at":card_fetched.isoformat(),"sha256":card_sha},
         "beforeinfo":before_audit},
       "racers":racers,"beforeinfo":beforeinfo}
