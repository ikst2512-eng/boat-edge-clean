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
