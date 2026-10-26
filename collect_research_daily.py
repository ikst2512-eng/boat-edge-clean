"""Daily research forecast collection. Uses one source fetch per daily CSV."""
import argparse, csv, io, json, os, sys
import math
from collections import Counter
from datetime import datetime, timedelta
from research_model import JST, BASE, STORE, _record_path, _saved, probabilities, read_rows
def collect(day):
    date=datetime.strptime(day,"%Y%m%d").date()
    if date<=datetime(2026,10,21).date():raise ValueError("training days excluded")
    path=f"{day[:4]}/{day[4:6]}/{day[6:]}.csv"
    titles,t1=read_rows(BASE+"title/"+path)
    cards,t2=read_rows(BASE+"race_cards/"+path)
    # Duplicate source keys are ambiguous: never silently take the last row.
    card_counts=Counter(r.get("レースコード") for r in cards if isinstance(r,dict) and r.get("レースコード"))
    title_counts=Counter(r.get("レースコード") for r in titles if isinstance(r,dict) and r.get("レースコード"))
    eligible_codes={r.get("レースコード") for r in titles if isinstance(r,dict) and isinstance(r.get("レースコード"),str) and r["レースコード"].isascii() and r["レースコード"].isdigit() and len(r["レースコード"])==12 and r["レースコード"].startswith(day)}
    if not eligible_codes:
        raise ValueError("no valid race titles for requested day")
    if not cards:
        raise ValueError("race card source is empty")
    by_code={r["レースコード"]:r for r in cards if isinstance(r,dict) and r.get("レースコード") and card_counts[r["レースコード"]]==1}
    counts={"saved":0,"already_saved":0,"not_ready":0,"missing":0,"invalid":0}
    counted_duplicates=set()
    for title in titles:
        code=title.get("レースコード","") if isinstance(title,dict) else ""
        if not(code.isascii() and code.isdigit() and len(code)==12 and code.startswith(day)):continue
        if title_counts[code]!=1 or card_counts[code]>1:
            if code not in counted_duplicates:
                counts["invalid"]+=1
                counted_duplicates.add(code)
            continue
        card=by_code.get(code)
        if card is None:counts["missing"]+=1;continue
        try:
            old=_saved(code)
            if old is not None:counts["already_saved"]+=1;continue
            deadline=datetime.strptime(day+title["電話投票締切予定"],"%Y%m%d%H:%M").replace(tzinfo=JST)
            now=datetime.now(JST);cutoff=deadline-timedelta(minutes=12)
            if max(now,t1,t2)>cutoff:counts["not_ready"]+=1;continue
            rates=[float(card[f"艇{i}_全国勝率"]) for i in range(1,7)]
            if any(not math.isfinite(rate) or not 0 <= rate <= 10 for rate in rates):
                raise ValueError("invalid national win rate")
            tickets=["-".join(map(str,t)) for t,_ in probabilities(rates)[:10]]
            record={"ok":True,"status":"research","validated":False,"race_code":code,"predictions":tickets,
                "model_version":"national-beta0.4-exploratory-v1","generated_at":now.isoformat(),
                "message":"研究予想（未検証・回収率未確認）","cutoff_jst":cutoff.isoformat(),
                "source_deadline_jst":deadline.isoformat(),
                "source_title_received_jst":t1.isoformat(),"source_cards_received_jst":t2.isoformat(),
                "national_win_rates":rates}
            STORE.mkdir(parents=True,exist_ok=True)
            with _record_path(code).open("x",encoding="utf-8") as f:
                json.dump(record,f,ensure_ascii=False,sort_keys=True)
                f.flush();os.fsync(f.fileno())
            counts["saved"]+=1
        except FileExistsError:counts["already_saved"]+=1
        except (ValueError, KeyError, TypeError, OSError) as e:counts["invalid"]+=1
    return counts

def validate_run_counts(counts):
    """Treat a fully invalid scheduled capture as failure, not an empty success."""
    if counts["saved"]+counts["already_saved"]+counts["not_ready"]==0:
        raise ValueError("no valid or cutoff-eligible race records; refusing green run")
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--date",default=datetime.now(JST).strftime("%Y%m%d"))
    a=p.parse_args()
    result=collect(a.date)
    print(json.dumps(result,ensure_ascii=False))
    validate_run_counts(result)
