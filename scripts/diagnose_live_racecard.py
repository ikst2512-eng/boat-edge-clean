"""Live source diagnostic. Never writes forecasts or results."""
from datetime import datetime
from urllib.error import HTTPError, URLError
from clean_direct_sources import holding_rows
from clean_racecard import racecard, _preview_rows
from research_model import JST

def run():
    day=datetime.now(JST).strftime("%Y%m%d")
    print("DIAGNOSTIC_DATE",day,flush=True)
    try:
        titles,received,sha=holding_rows(day)
    except (HTTPError, URLError, ValueError, OSError, TimeoutError) as e:
        print("HOLDING_SOURCE_ERROR",type(e).__name__,str(e)[:120],flush=True)
        try:
            from clean_openapi_sources import load
            titles,cards,received,digest,meta=load(day)
            print("OPENAPI_SOURCE_OK",len(titles),"races",len(cards),"cards",meta["source"],flush=True)
            for row in titles[:3]:
                print("OPENAPI_RACE",row["レースコード"],row["電話投票締切予定"],flush=True)
        except (HTTPError,URLError,ValueError,OSError,TimeoutError,KeyError) as alt:
            print("OPENAPI_SOURCE_ERROR",type(alt).__name__,str(alt)[:120],flush=True)
            raise RuntimeError("ALL_LIVE_SCHEDULE_SOURCES_UNAVAILABLE") from alt
    print("HOLDING_SOURCE_ROWS",len(titles),flush=True)
    now=datetime.now(JST)
    upcoming=[]
    for row in titles:
        try:
            deadline=datetime.strptime(day+row["電話投票締切予定"],"%Y%m%d%H:%M").replace(tzinfo=JST)
            if deadline>now:upcoming.append((deadline,row["レースコード"]))
        except (KeyError,ValueError):continue
    upcoming.sort()
    window=[x for x in upcoming if 120 < (x[0]-now).total_seconds() <= 1320]
    chosen=(window+[x for x in upcoming if x not in window])[:3]
    print("UPCOMING_RACES",len(upcoming),"PREVIEW_WINDOW_RACES",len(window),flush=True)
    seen_preview={}
    for kind in ("tkz","stt","sui"):
        try:
            rows,sha=_preview_rows(kind,f"{day[:4]}/{day[4:6]}/{day[6:8]}.csv")
            eligible={x[1]:x[0] for x in upcoming}
            matched=set()
            for row in rows:
                code=row.get("レースコード")
                if code not in eligible or row.get("締切時刻")!=eligible[code].strftime("%H:%M"):continue
                try:
                    timestamp=datetime.fromisoformat(row.get("取得日時",""))
                except (ValueError,TypeError):continue
                if timestamp.tzinfo and timestamp<=now and timestamp<eligible[code]:matched.add(code)
            seen_preview[kind]=matched
            observed=len(matched & {x[1] for x in window})
            print("PREVIEW_SOURCE",kind,"rows",len(rows),"near_deadline_matches",observed,"sha256",sha,flush=True)
        except (HTTPError,URLError,ValueError,OSError,TimeoutError,KeyError) as e:
            print("PREVIEW_SOURCE_ERROR",kind,type(e).__name__,str(e)[:120],flush=True)
    if "tkz" in seen_preview and "stt" in seen_preview:
        published=seen_preview["tkz"] & seen_preview["stt"]
        priority=[x for x in upcoming if x[1] in published]
        chosen=(priority+[x for x in chosen if x not in priority])[:3]
        print("PUBLISHED_PREDEADLINE_PREVIEW_CANDIDATES",len(priority),"SELECTED",[x[1] for x in chosen],flush=True)
    for _,code in chosen:
        try:
            card=racecard(day,str(int(code[8:10])),str(int(code[10:12])))
            print("RACECARD_OK",code,"racers",len(card["racers"]),"source",card["meta"]["source"],"preview",card["source_audit"]["beforeinfo"]["status"],"source_status",card["source_audit"]["beforeinfo"].get("source_status"),flush=True)
        except (HTTPError,URLError,ValueError,OSError,TimeoutError,KeyError,TypeError) as e:
            print("RACECARD_ERROR",code,type(e).__name__,str(e)[:120],flush=True)

if __name__=="__main__":run()
