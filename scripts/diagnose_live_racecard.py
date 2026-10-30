"""Live source diagnostic. Never writes forecasts or results."""
from datetime import datetime
from urllib.error import HTTPError, URLError
from clean_direct_sources import holding_rows
from clean_racecard import racecard
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
            return
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
    for _,code in chosen:
        try:
            card=racecard(day,str(int(code[8:10])),str(int(code[10:12])))
            print("RACECARD_OK",code,"racers",len(card["racers"]),"source",card["meta"]["source"],"preview",card["source_audit"]["beforeinfo"]["status"],"source_status",card["source_audit"]["beforeinfo"].get("source_status"),flush=True)
        except (HTTPError,URLError,ValueError,OSError,TimeoutError,KeyError,TypeError) as e:
            print("RACECARD_ERROR",code,type(e).__name__,str(e)[:120],flush=True)

if __name__=="__main__":run()
