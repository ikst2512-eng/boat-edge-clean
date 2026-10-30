"""Live source diagnostic. Never writes forecasts or results."""
from datetime import datetime
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import json
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
            # Compare the same race at the real Render API; never infer live
            # publication from a successful local source fetch alone.
            url=("https://boat-edge-clean.onrender.com/api/clean-racecard?hd="+day+
                 "&jcd="+str(int(code[8:10]))+"&rno="+str(int(code[10:12])))
            try:
                with urlopen(Request(url,headers={"User-Agent":"CLEAN-SOURCE-PARITY/1.0"}),timeout=12) as response:
                    live=json.load(response)
                    if response.status!=200:raise ValueError("render_http_non_200")
                expected=f"{day}-{code[8:10]}-{code[10:12]}"
                if live.get("race_key")!=expected or len(live.get("racers",[]))!=6:
                    raise ValueError("render_race_identity_or_six_boats_invalid")
                live_audit=live.get("source_audit",{}).get("beforeinfo",{})
                print("RENDER_PREVIEW_COMPARISON",code,"local",card["source_audit"]["beforeinfo"]["status"],
                      "render",live_audit.get("status"),"render_sources",live_audit.get("source_status"),flush=True)
                local_status=card["source_audit"]["beforeinfo"]["status"]
                render_status=live_audit.get("status")
                if local_status=="ok" and render_status!="ok":
                    print("SOURCE_RENDER_PREVIEW_DIVERGENCE",code,
                          "source_verified_render_unavailable",render_status,
                          live_audit.get("source_status"),flush=True)
                elif local_status!="ok" and render_status=="ok":
                    print("SOURCE_RENDER_PREVIEW_DIVERGENCE",code,
                          "render_verified_source_unavailable",local_status,flush=True)
                if card["source_audit"]["beforeinfo"]["status"]=="ok" and live_audit.get("status")=="ok":
                    if len((live.get("beforeinfo") or {}).get("racers",[]))!=6 or len((live.get("beforeinfo") or {}).get("start_exhibition",[]))!=6:
                        raise ValueError("render_verified_preview_incomplete")
                    local_preview=card.get("beforeinfo") or {}
                    remote_preview=live.get("beforeinfo") or {}
                    local_sources=card["source_audit"]["beforeinfo"].get("sources") or {}
                    remote_sources=live_audit.get("sources") or {}
                    same_snapshots=all(
                        local_sources.get(kind,{}).get("sha256")
                        and local_sources[kind]["sha256"]==remote_sources.get(kind,{}).get("sha256")
                        for kind in ("tkz","stt")
                    )
                    if same_snapshots:
                        for section,keys in (("racers",("lane","exhibition_time","tilt")),
                                             ("start_exhibition",("lane","course","st"))):
                            lhs=[tuple(row.get(k) for k in keys) for row in local_preview.get(section,[])]
                            rhs=[tuple(row.get(k) for k in keys) for row in remote_preview.get(section,[])]
                            if lhs!=rhs:raise ValueError("RENDER_PREVIEW_VALUE_MISMATCH_"+section)
                        print("LOCAL_AND_RENDER_SIX_BOAT_PREVIEW_VALUE_PASS",code,flush=True)
                    else:
                        print("LOCAL_RENDER_PREVIEW_DIFFERENT_SNAPSHOT_NOT_A_VALUE_PASS",code,flush=True)
            except ValueError as remote:
                if str(remote).startswith("RENDER_PREVIEW_VALUE_MISMATCH_"):
                    print("RENDER_PREVIEW_VALUES_MISMATCH",code,str(remote),flush=True)
                    raise RuntimeError("RENDER_PREVIEW_VALUES_MISMATCH_"+code) from remote
                print("RENDER_PREVIEW_COMPARISON_INVALID",code,str(remote)[:120],flush=True)
            except (HTTPError,URLError,OSError,TimeoutError,KeyError,TypeError) as remote:
                print("RENDER_PREVIEW_COMPARISON_UNAVAILABLE",code,type(remote).__name__,str(remote)[:120],flush=True)
            audit=card["source_audit"]["beforeinfo"]
            if audit["status"]=="ok":
                preview=card.get("beforeinfo") or {}
                ex=preview.get("racers") or []
                starts=preview.get("start_exhibition") or []
                if len(ex)!=6 or len(starts)!=6:
                    raise ValueError("VERIFIED_PREVIEW_INCOMPLETE")
                if sorted(int(r["lane"]) for r in ex)!=list(range(1,7)):
                    raise ValueError("VERIFIED_PREVIEW_LANES_INVALID")
                if sorted(int(r["course"]) for r in starts)!=list(range(1,7)):
                    raise ValueError("VERIFIED_PREVIEW_COURSES_INVALID")
                print("LOCAL_SIX_BOAT_PREVIEW_PASS",code,"observed_at",audit["fetched_at"],flush=True)
            else:
                print("LOCAL_SIX_BOAT_PREVIEW_NOT_VERIFIED",code,audit["status"],flush=True)
        except (HTTPError,URLError,ValueError,OSError,TimeoutError,KeyError,TypeError) as e:
            print("RACECARD_ERROR",code,type(e).__name__,str(e)[:120],flush=True)

if __name__=="__main__":run()
