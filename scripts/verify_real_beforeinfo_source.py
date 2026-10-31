"""Read actual BoatraceCSV source files, never fixture data, and report schema/evidence."""
import json
import sys
from pathlib import Path
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from clean_racecard import _preview_rows

def main(day=None):
    day=day or (datetime.now(ZoneInfo("Asia/Tokyo"))-timedelta(days=1)).strftime("%Y/%m/%d.csv")
    evidence={}
    for kind in ("tkz","stt","sui"):
        rows,sha=_preview_rows(kind,day)
        if not rows:
            raise RuntimeError(kind+": no source rows")
        keys=rows[0].keys()
        expected={"レースコード","締切時刻","取得日時"}
        if kind=="tkz":
            expected|={f"艇{i}_{field}" for i in range(1,7) for field in ("展示タイム","チルト")}
        if kind=="stt":
            expected|={f"艇{i}_{field}" for i in range(1,7) for field in ("コース","スタート展示")}
        if not expected.issubset(keys):
            raise RuntimeError(kind+": unexpected columns "+str(sorted(expected-set(keys))))
        evidence[kind]={"rows":len(rows),"sha256":sha,"first_race":rows[0]["レースコード"],
                        "columns_verified":sorted(expected)}
    # Verify real race rows can actually feed the CLEAN adapter, not just match column names.
    from clean_racecard import _fetch_preview
    from research_model import JST
    matched=[]
    tkz_rows,_=_preview_rows("tkz",day)
    for row in tkz_rows:
        code=row.get("レースコード","")
        clock=row.get("締切時刻","")
        if len(code)!=12 or not clock:continue
        try:
            deadline=datetime.strptime(code[:8]+clock,"%Y%m%d%H:%M").replace(tzinfo=JST)
            preview,audit=_fetch_preview(code,day,deadline)
            if audit.get("status")=="ok" and preview and len(preview.get("racers",[]))==6:
                exhibition = preview["racers"]
                starts = preview["start_exhibition"]
                evidence["verified_six_boat_fields"] = {
                    "exhibition_times": sum(r.get("exhibition_time") is not None for r in exhibition),
                    "tilts": sum(r.get("tilt") is not None for r in exhibition),
                    "actual_courses": sum(r.get("course") is not None for r in starts),
                    "start_exhibition": sum(r.get("st") is not None for r in starts),
                    "course_permutation_valid": sorted(r["course"] for r in starts) == [1., 2., 3., 4., 5., 6.],
                    "source_status": audit.get("source_status"),
                }
                matched.append(code)
                break
        except (ValueError,KeyError):
            continue
    if not matched:
        raise RuntimeError("REAL_BEFOREINFO_NO_VERIFIED_RACE: source columns exist but no actual race passes full adapter checks")
    evidence["verified_race_code"]=matched[0]
    print(json.dumps({"source":"BoatraceCSV real HTTPS","day":day,"evidence":evidence},ensure_ascii=False))
if __name__=="__main__":
    main(sys.argv[1] if len(sys.argv)>1 else None)
