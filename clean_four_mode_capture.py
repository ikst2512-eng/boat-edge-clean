"""Freeze independent CLEAN four-mode forecasts for races still ahead.

Reads published pre-race title/cards once per day. Does not read the legacy
repository, final results, payouts, or optional unprovided exhibition fields.
Write-once archives are committed separately by the existing scheduled action.
"""
import hashlib
import json
import os
from urllib.error import HTTPError, URLError
from datetime import datetime, timedelta
from pathlib import Path

from research_model import JST, BASE, read_rows, probabilities
from clean_four_modes import rank_modes

ROOT=Path(__file__).resolve().parent
ARCHIVE=ROOT/"four_mode_forecasts"


def collect(root=ROOT, now=None, read=read_rows):
    now=now or datetime.now(JST)
    hd=now.strftime("%Y%m%d")
    sub=f"{hd[:4]}/{hd[4:6]}/{hd[6:8]}.csv"
    titles,title_received,title_sha=read(BASE+"title/"+sub)
    cards,card_received,card_sha=read(BASE+"race_cards/"+sub)
    cards_by_code={r.get("レースコード"):r for r in cards}
    out=root/"four_mode_forecasts"
    saved,excluded=[],{}
    for title in titles:
        code=title.get("レースコード","")
        if len(code)!=12 or not code.isdecimal() or not code.startswith(hd):
            continue
        try:
            venue,race=int(code[8:10]),int(code[10:12])
            if not 1<=venue<=24 or not 1<=race<=12:
                raise ValueError("race_code")
            cutoff=datetime.strptime(hd+title["電話投票締切予定"],"%Y%m%d%H:%M").replace(tzinfo=JST)
            # Allow GitHub commit time before the actual deadline.
            if max(now,title_received,card_received)>cutoff-timedelta(minutes=20):
                continue
            path=out/(code+".json")
            if path.is_symlink():raise ValueError("symlink")
            if path.exists():continue
            racer=cards_by_code.get(code)
            if not racer:raise ValueError("missing_race_card")
            rates=[float(racer[f"艇{i}_全国勝率"]) for i in range(1,7)]
            forecast=rank_modes(probabilities(rates))
            record={"schema":"CLEAN_FOUR_MODES_PREDEADLINE_V1","race_code":code,
                    "status":"provisional","validated":False,
                    "model_version":"CLEAN_FOUR_MODES_V1_UNCALIBRATED",
                    "deadline_jst":cutoff.isoformat(),"generated_at_jst":now.isoformat(),
                    "beforeinfo":"optional_not_in_snapshot",
                    "source_sha256":{"title":title_sha,"race_cards":card_sha},
                    "input_national_win_rates":rates,
                    "target_rates_not_proven":True,"modes":forecast}
            out.mkdir(parents=True,exist_ok=True)
            with path.open("x",encoding="utf-8") as f:
                json.dump(record,f,ensure_ascii=False,sort_keys=True,indent=2)
                f.write("\n")
                f.flush()
                os.fsync(f.fileno())
            saved.append(code)
        except (KeyError,ValueError,TypeError,OSError) as exc:
            label=str(exc)[:64] or type(exc).__name__
            excluded[label]=excluded.get(label,0)+1
    return {"new_saved":saved,"excluded":excluded}


if __name__=="__main__":
    try:
        result=collect()
    except HTTPError as exc:
        result={"new_saved":[],"source_pending":"HTTPError","http_status":exc.code,
                "source_url":exc.url,"retryable":True}
    except (URLError, TimeoutError, ConnectionError) as exc:
        result={"new_saved":[],"source_pending":type(exc).__name__,"retryable":True}
    print(json.dumps(result,ensure_ascii=False))
