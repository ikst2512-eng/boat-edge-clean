"""Observe TODAY's actual predeadline preview availability without retroactive scoring."""
from datetime import datetime
from zoneinfo import ZoneInfo
from urllib.error import HTTPError, URLError
from clean_racecard import _preview_rows

now=datetime.now(ZoneInfo("Asia/Tokyo"))
day=now.strftime("%Y/%m/%d.csv")
print("PROBE_DAY",day,"NOW_JST",now.isoformat(),flush=True)
sources={}
for kind in ("tkz","stt","sui"):
    try:
        rows,digest=_preview_rows(kind,day)
        before=[]
        for row in rows:
            try:
                if not row.get("レースコード","").startswith(now.strftime("%Y%m%d")):continue
                observed=datetime.fromisoformat(row.get("取得日時",""))
                deadline=datetime.strptime(row["レースコード"][:8]+row["締切時刻"],"%Y%m%d%H:%M").replace(tzinfo=ZoneInfo("Asia/Tokyo"))
                if observed.tzinfo and observed<=now and observed<deadline and now<deadline:
                    before.append(row["レースコード"])
            except (ValueError,KeyError,TypeError):pass
        sources[kind]=set(before)
        print("PREVIEW",kind,"rows",len(rows),"eligible_future",len(before),"sha256",digest,flush=True)
    except (HTTPError,URLError,OSError,ValueError,TimeoutError) as exc:
        print("PREVIEW",kind,"unavailable",type(exc).__name__,str(exc)[:120],flush=True)
print("MATCHED_CURRENT_PREDEADLINE",len(sources.get("tkz",set())&sources.get("stt",set())),flush=True)

# One adapter check per eligible race. The cutoff must come from tkz rows,
# not the final CSV fetched by the preceding source loop.
from clean_racecard import _fetch_preview
eligible=sorted(sources.get("tkz",set()) & sources.get("stt",set()))
verified=[]
if eligible:
    tkz_rows,_=_preview_rows("tkz",day)
    cutoff_by_code={row.get("レースコード"):row.get("締切時刻") for row in tkz_rows}
    for code in eligible[:6]:
        try:
            deadline_text=cutoff_by_code.get(code)
            if not deadline_text:
                print("ADAPTER_ERROR",code,"missing_tkz_deadline",flush=True)
                continue
            deadline=datetime.strptime(code[:8]+deadline_text,"%Y%m%d%H:%M").replace(tzinfo=ZoneInfo("Asia/Tokyo"))
            preview,audit=_fetch_preview(code,day,deadline)
            if audit.get("status")=="ok" and len((preview or {}).get("racers",[]))==6 and len((preview or {}).get("start_exhibition",[]))==6:
                verified.append(code)
                print("VERIFIED_SIX_LANE",code,"source",audit.get("source"),flush=True)
            else:
                print("SIX_LANE_NOT_VERIFIED",code,audit.get("status"),flush=True)
        except (OSError,ValueError,KeyError,TypeError,TimeoutError) as exc:
            print("ADAPTER_ERROR",code,type(exc).__name__,flush=True)
print("ADAPTER_VERIFIED_CURRENT_PREDEADLINE",len(verified),",".join(verified),flush=True)
