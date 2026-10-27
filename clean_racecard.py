"""Independent CLEAN pre-race card adapter from documented public BoatraceCSV fields."""
from datetime import datetime
import re
from research_model import BASE,JST,read_rows


def _num(v):
    try:
        return float(v) if v not in (None,"","-") else None
    except (ValueError,TypeError):
        return None


def racecard(hd,jcd,rno):
    if not re.fullmatch(r"20\d{6}",str(hd)) or not re.fullmatch(r"0[1-9]|1[0-9]|2[0-4]",str(jcd)) or not re.fullmatch(r"[1-9]|1[0-2]",str(rno)):
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
    for i in range(1,7):
        p=f"艇{i}_"
        number=str(fields.get(p+"登録番号","")).strip()
        if not re.fullmatch(r"\d{4}",number):raise ValueError("six_racers_unavailable")
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
    return {"schema_version":"boat-edge-race-v5","race_key":f"{hd}-{int(jcd):02d}-{int(rno):02d}",
       "meta":{"date":f"{hd[:4]}-{hd[4:6]}-{hd[6:8]}","venue_code":f"{int(jcd):02d}","race_no":int(rno),
         "deadline":deadline_text,"phase":"PRE_RESULT","results_seen":False,"unlock":False,"scoring":False,
         "source":"CLEAN_PUBLIC_PRE_RACE_CSV"},
       "source_audit":{"race_card":{"status":"ok","fetched_at":card_fetched.isoformat(),"sha256":card_sha},
         "beforeinfo":{"status":"not_collected"}},
       "racers":racers,"beforeinfo":None}
