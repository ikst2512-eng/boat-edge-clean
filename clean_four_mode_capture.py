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
    # Probe both independent upstream datasets, even when the first is missing.
    # This avoids hiding race-card availability behind a title 404.
    outcomes={}
    datasets={}
    for kind in ("title","race_cards"):
        url=BASE+kind+"/"+sub
        try:
            datasets[kind]=read(url)
            outcomes[kind]={"status":"available","rows":len(datasets[kind][0])}
        except HTTPError as exc:
            outcomes[kind]={"status":"not_published" if exc.code==404 else "http_error","http_status":exc.code,"source_url":url}
        except (URLError,TimeoutError,ConnectionError,OSError) as exc:
            outcomes[kind]={"status":"network_error","error_type":type(exc).__name__,"source_url":url}
    direct_meta={}
    if len(datasets)!=2:
        # The daily third-party files may be published only after the race.
        # Fetch directly from their documented pre-race origin, within bounds.
        from clean_direct_sources import holding_rows,direct_cards
        try:
            if "title" not in datasets:
                datasets["title"]=holding_rows(hd)
                outcomes["title_direct"]={"status":"available","rows":len(datasets["title"][0])}
            title_rows,recv_title,sha_title=datasets["title"]
            old_archive=root/"four_mode_forecasts"
            existing={p.stem for p in old_archive.glob(hd+"*.json")} if old_archive.exists() else set()
            if "race_cards" not in datasets:
                direct,received,combined,hashes,failed=direct_cards(hd,title_rows,existing,now=now)
                outcomes["race_cards_direct"]={"status":"available" if direct else "unavailable",
                    "rows":len(direct),"failed":failed,"requested_limit":18}
                direct_meta=hashes
                if direct:datasets["race_cards"]=(direct,received,combined)
        except (HTTPError,URLError,TimeoutError,ValueError,OSError,UnicodeError) as exc:
            outcomes["direct_error"]={"status":"error","type":type(exc).__name__,
                "http_status":getattr(exc,"code",None),
                "source_url":getattr(exc,"url",None)}
    if len(datasets)!=2:
        return {"new_saved":[],"excluded":{},"date_jst":hd,
                "source_status":"source_incomplete","source_probes":outcomes,
                "eligible_forecasts_today":len(list((root/"four_mode_forecasts").glob(hd+"*.json"))) if (root/"four_mode_forecasts").exists() else 0}
    titles,title_received,title_sha=datasets["title"]
    cards,card_received,card_sha=datasets["race_cards"]
    title_counts={}
    for title in titles:
        code=title.get("レースコード")
        title_counts[code]=title_counts.get(code,0)+1
    cards_by_code={}
    duplicate_codes=set()
    for card in cards:
        code=card.get("レースコード")
        if code in cards_by_code:
            duplicate_codes.add(code)
        else:
            cards_by_code[code]=card
    for code in duplicate_codes:
        cards_by_code.pop(code,None)
    out=root/"four_mode_forecasts"
    saved,excluded=[],{}
    for title in titles:
        code=title.get("レースコード","")
        if len(code)!=12 or not code.isdecimal() or not code.startswith(hd):
            continue
        try:
            if title_counts[code]!=1:raise ValueError("duplicate_title")
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
                    "source_sha256":{"title":title_sha,"race_cards":direct_meta.get(code,card_sha)},
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
    return {"new_saved":saved,"excluded":excluded,"source_probes":outcomes,"date_jst":hd,
            "published_title_rows":len(titles),"published_card_rows":len(cards),
            "source_status":"available" if cards else "empty_cards",
            "eligible_forecasts_today":len(list(out.glob(hd+"*.json"))) if out.exists() else 0}


def publish_status(result,root=ROOT,now=None):
    """Small stable diagnostic; do not overwrite any forecast evidence."""
    now=now or datetime.now(JST)
    day=now.strftime("%Y%m%d")
    state={"schema":"CLEAN_FOUR_MODE_CAPTURE_HEALTH_V1","day_jst":day,
           "source_status":result.get("source_status",result.get("source_pending","unknown")),
           "http_status":result.get("http_status"),
           "source_url":result.get("source_url"),
           "source_probes":result.get("source_probes",{}),
           "published_title_rows":result.get("published_title_rows"),
           "published_card_rows":result.get("published_card_rows"),
           "eligible_forecasts_today":result.get("eligible_forecasts_today",0),
           "excluded":result.get("excluded",{}),
           "last_run_new_count":len(result.get("new_saved",[])),
           "production_success_proven":result.get("eligible_forecasts_today",0)>0}
    target=root/"four_mode_forecasts"/"capture_status.json"
    target.parent.mkdir(parents=True,exist_ok=True)
    content=json.dumps(state,ensure_ascii=False,sort_keys=True,indent=2)+chr(10)
    if not target.exists() or target.read_text(encoding="utf-8")!=content:
        target.write_text(content,encoding="utf-8")
    return state


if __name__=="__main__":
    try:
        result=collect()
    except HTTPError as exc:
        result={"new_saved":[],"source_pending":"waiting_for_published_source" if exc.code==404 else "HTTPError","http_status":exc.code,
                "source_url":exc.url,"retryable":True}
    except (URLError, TimeoutError, ConnectionError) as exc:
        result={"new_saved":[],"source_pending":type(exc).__name__,"retryable":True}
    publish_status(result)
    print(json.dumps(result,ensure_ascii=False))
