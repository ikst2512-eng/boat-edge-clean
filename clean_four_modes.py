"""CLEAN independent four-mode prospective forecasts. Targets are goals, not attained rates."""
from datetime import datetime, timedelta
from research_model import JST, BASE, read_rows, probabilities
import hashlib
import math
import re
import json
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

TARGETS={"hit":0.60,"balance":0.50,"hole":0.125,"narrow":0.40}
LABELS={"hit":"本命","balance":"バランス","hole":"穴","narrow":"絞り"}


def rank_modes(prob_rows):
    """Different mode memberships, uncalibrated until forward evaluation."""
    rows=[("-".join(map(str,t)),float(p)) for t,p in prob_rows]
    if len(rows)!=120 or abs(sum(p for _,p in rows)-1)>1e-6:
        raise ValueError("probability_board_invalid")
    hit=rows[:]
    # Spread balance candidates across different 1st/2nd-place branches.
    # Never hardcode a particular lane as favored.
    remaining=list(rows)
    balance=[]
    while remaining:
        firsts={x[0][0] for x in balance}
        pairs={x[0][:3] for x in balance}
        best=max(remaining,key=lambda x:(x[1]*(1.0+(0.30 if x[0][0] not in firsts else 0)+(0.15 if x[0][:3] not in pairs else 0)),-int(x[0][0]),-int(x[0][2]),-int(x[0][4])))
        remaining.remove(best)
        balance.append(best)
    # Hole is low-probability coverage, NOT a fabricated high-odds forecast.
    hole=sorted(rows,key=lambda item:(abs(item[1]-0.004),-item[1],item[0]))
    narrow=rows[:]
    ordering={"hit":hit,"balance":balance,"hole":hole,"narrow":narrow}
    caps={"hit":30,"balance":20,"hole":12,"narrow":5}
    modes={}
    for name,ordered in ordering.items():
        target=TARGETS[name]
        selected=[]
        total=0.0
        for combo,p in ordered:
            selected.append({"combo":combo,"p":round(p*100,5)})
            total+=p
            if total>=target or len(selected)>=caps[name]:
                break
        modes[name]={"tickets":selected,"estimated_coverage_pct":round(total*100,2),
                     "target_hit_rate_pct":round(target*100,1),
                     "target_met_by_estimate":total>=target,
                     "actual_hit_rate_pct":None}
    return modes


def load_archived(code):
    path=Path(__file__).resolve().parent/"four_mode_forecasts"/(code+".json")
    if path.is_symlink():raise ValueError("archive_symlink")
    if path.is_file():
        raw=path.read_bytes()
    else:
        url="https://raw.githubusercontent.com/ikst2512-eng/boat-edge-clean/main/four_mode_forecasts/"+code+".json"
        try:
            with urlopen(Request(url,headers={"User-Agent":"CLEAN-FOUR-MODES/1.0"}),timeout=4) as response:
                raw=response.read(30001)
        except HTTPError as exc:
            if exc.code==404:return None
            raise
        except (URLError,TimeoutError,OSError):
            return None
    if len(raw)>30000:raise ValueError("archive_oversize")
    d=json.loads(raw)
    if (not isinstance(d,dict) or d.get("race_code")!=code or
        d.get("schema")!="CLEAN_FOUR_MODES_PREDEADLINE_V1" or
        d.get("target_rates_not_proven") is not True or
        not isinstance(d.get("modes"),dict)):
        raise ValueError("archive_invalid")
    saved=datetime.fromisoformat(d["generated_at_jst"])
    deadline=datetime.fromisoformat(d["deadline_jst"])
    if not saved.utcoffset() or not deadline.utcoffset() or saved>=deadline:
        raise ValueError("archive_time_invalid")
    return {"ok":True,"status":"provisional","validated":False,
            "snapshot_type":"archived_proof_pending",
            "model_version":d["model_version"],"race_code":code,
            "deadline_jst":d["deadline_jst"],"generated_at_jst":d["generated_at_jst"],
            "source_sha256":d["source_sha256"],
            "beforeinfo":d.get("beforeinfo"),"targets_are_not_realized_hit_rates":True,
            "modes":d["modes"]}


def forecast(hd,jcd,rno):
    if not re.fullmatch(r"20\d{6}",str(hd)) or not re.fullmatch(r"0[1-9]|1[0-9]|2[0-4]",str(jcd)) or not re.fullmatch(r"[1-9]|1[0-2]",str(rno)):
        raise ValueError("race_input_invalid")
    datetime.strptime(hd,"%Y%m%d")
    code=f"{hd}{int(jcd):02d}{int(rno):02d}"
    archived=load_archived(code)
    if archived is not None:return archived
    file=f"{hd[:4]}/{hd[4:6]}/{hd[6:8]}.csv"
    titles,received_title,sha_title=read_rows(BASE+"title/"+file)
    cards,received_card,sha_card=read_rows(BASE+"race_cards/"+file)
    title=[r for r in titles if r.get("レースコード")==code]
    card=[r for r in cards if r.get("レースコード")==code]
    if len(title)!=1 or len(card)!=1:
        raise ValueError("race_not_published")
    deadline=datetime.strptime(hd+title[0]["電話投票締切予定"],"%Y%m%d%H:%M").replace(tzinfo=JST)
    now=datetime.now(JST)
    if max(now,received_title,received_card)>=deadline:
        raise ValueError("race_deadline_passed")
    rates=[float(card[0][f"艇{i}_全国勝率"]) for i in range(1,7)]
    modes=rank_modes(probabilities(rates))
    return {"ok":True,"status":"provisional","validated":False,
            "model_version":"CLEAN_FOUR_MODES_V1_UNCALIBRATED",
            "race_code":code,"deadline_jst":deadline.isoformat(),"generated_at_jst":now.isoformat(),
            "source_sha256":{"title":sha_title,"race_cards":sha_card},
            "beforeinfo":"not_required_when_unavailable",
            "targets_are_not_realized_hit_rates":True,"modes":modes}
