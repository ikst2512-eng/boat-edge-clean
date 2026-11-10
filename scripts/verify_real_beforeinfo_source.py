"""Read actual BoatraceCSV source files, never fixture data, and report schema/evidence."""
import json
import re
import sys
from pathlib import Path
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from clean_racecard import _preview_rows

def verify_current_adapter(day, now=None, schedule_fetch=None, card_fetch=None):
    """Require a real current, still-open six-boat adapter response.

    Historical CSV schemas cannot prove a new predeadline HTTP receipt.
    """
    from research_model import JST
    from clean_schedule import clean_schedule
    from clean_racecard import racecard
    now = now or datetime.now(JST)
    if day != now.strftime("%Y/%m/%d.csv"):
        return []
    hd = now.strftime("%Y%m%d")
    status, schedule = (schedule_fetch or clean_schedule)(hd)
    if status != 200:
        return []
    candidates = sorted((r for r in schedule.get("races", [])
                         if datetime.fromisoformat(r["deadline_jst"]) > now),
                        key=lambda r: r["deadline_jst"])
    for race in candidates[:3]:
        try:
            data = (card_fetch or racecard)(hd, race["venue_code"], str(race["race_no"]))
            info, audit = data.get("beforeinfo") or {}, data.get("source_audit", {}).get("beforeinfo", {})
            deadline = datetime.fromisoformat(race["deadline_jst"])
            observed = datetime.fromisoformat(audit.get("fetched_at", ""))
            expected = hd + "-" + race["venue_code"] + "-" + str(race["race_no"]).zfill(2)
            exhibits = info.get("racers", [])
            six = (sorted(r["lane"] for r in exhibits) == list(range(1,7))
                   and all(type(r.get("exhibition_time")) in (int,float)
                           and 5 <= r["exhibition_time"] <= 9
                           and type(r.get("tilt")) in (int,float) and -1 <= r["tilt"] <= 3
                           for r in exhibits))
            starts = info.get("start_exhibition", [])
            if (data.get("race_key") == expected and audit.get("status") == "ok"
                    and observed.utcoffset() is not None and observed < deadline and six
                    and sorted(r["lane"] for r in starts) == list(range(1,7))
                    and sorted(r["course"] for r in starts) == list(range(1,7))
                    and all(re.fullmatch(r"(?:F|L)?\.\d{1,2}|\d?\.\d{1,2}", str(r.get("st", "")).strip()) for r in starts)):
                return [{"race_code": race["race_code"], "source_audit": audit,
                         "exhibition_times": 6, "start_exhibition": 6,
                         "formal_t12_certified": False}]
        except (OSError, ValueError, KeyError, TypeError):
            continue
    return []

def main(day=None):
    day=day or datetime.now(ZoneInfo("Asia/Tokyo")).strftime("%Y/%m/%d.csv")
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
    timing={"verified_races_with_saved_forecast":0,"preview_available_at_forecast_generation":0,"preview_observed_after_forecast_generation":0,"forecast_metadata_missing_or_invalid":0}
    checked=0
    seen=set()
    status_counts={}
    tkz_rows,_=_preview_rows("tkz",day)
    snapshot_dir=Path(__file__).resolve().parents[1]/"research_snapshots"
    archive_codes={p.stem for p in snapshot_dir.glob("*.json")}
    candidates=sorted(tkz_rows,key=lambda row:(
        row.get("レースコード","") not in archive_codes,
        row.get("レースコード","")
    ))
    evidence["forecast_overlap_available"]=len({
        row.get("レースコード") for row in tkz_rows
        if row.get("レースコード") in archive_codes
    })
    for row in candidates:
        code=row.get("レースコード","")
        clock=row.get("締切時刻","")
        if len(code)!=12 or not clock or code in seen:continue
        try:
            deadline=datetime.strptime(code[:8]+clock,"%Y%m%d%H:%M").replace(tzinfo=JST)
        except (ValueError,TypeError):
            continue
        # Closed races cannot pass the adapter's real receipt clock. Skip
        # them before spending the six-race budget and more network fetches.
        if deadline <= datetime.now(JST):continue
        seen.add(code)
        if checked>=6:break
        checked+=1
        try:
            preview,audit=_fetch_preview(code,day,deadline)
            status=audit.get("status", "unknown")
            status_counts[status]=status_counts.get(status,0)+1
            if status=="ok" and preview and len(preview.get("racers",[]))==6:
                exhibition = preview["racers"]
                starts = preview["start_exhibition"]
                counts = {
                    "exhibition_times": sum(r.get("exhibition_time") is not None for r in exhibition),
                    "tilts": sum(r.get("tilt") is not None for r in exhibition),
                    "actual_courses": sum(r.get("course") is not None for r in starts),
                    "start_exhibition": sum(r.get("st") is not None for r in starts),
                    "course_permutation_valid": sorted(r["course"] for r in starts) == [1., 2., 3., 4., 5., 6.],
                    "source_status": audit.get("source_status"),
                }
                evidence.setdefault("verified_six_boat_fields", counts)
                if (any(counts[k] != 6 for k in ("exhibition_times", "tilts", "actual_courses", "start_exhibition"))
                    or counts["course_permutation_valid"] is not True
                    or any(counts["source_status"].get(k) != "ok" for k in ("tkz", "stt"))):
                    raise RuntimeError("REAL_BEFOREINFO_INCOMPLETE_SIX_BOAT_EVIDENCE")
                archive=Path(__file__).resolve().parents[1]/"research_snapshots"/(code+".json")
                if archive.is_file():
                    timing["verified_races_with_saved_forecast"]+=1
                    try:
                        saved=json.loads(archive.read_text(encoding="utf-8"))
                        generated=datetime.fromisoformat(saved["generated_at"])
                        observations=[datetime.fromisoformat(audit["sources"][kind]["observed_at"])
                                      for kind in ("tkz","stt")]
                        if (saved.get("race_code")!=code or generated.utcoffset() is None
                                or any(t.utcoffset() is None for t in observations)):
                            raise ValueError("unverified timestamp")
                        if max(observations)<=generated:
                            timing["preview_available_at_forecast_generation"]+=1
                        else:
                            timing["preview_observed_after_forecast_generation"]+=1
                    except (KeyError, ValueError, TypeError, OSError):
                        timing["forecast_metadata_missing_or_invalid"]+=1
                matched.append(code)
        except (ValueError,KeyError):
            continue
    if not matched:
        # A current official response can be complete while the CSV exporter
        # has not yet published this race. Use the production adapter itself;
        # do not backdate a historical fetch or turn an empty probe green.
        live = verify_current_adapter(day)
        evidence["live_adapter_observations"] = live
        matched = [item["race_code"] for item in live]
    if not matched:
        raise RuntimeError("REAL_BEFOREINFO_NO_VERIFIED_RACE: source columns exist but no actual race passes full adapter checks")
    evidence["verified_race_code"]=matched[0]
    evidence["coverage_sample"]={"checked":checked,"verified":len(matched),"statuses":status_counts,"verified_race_codes":matched}
    evidence["forecast_timing_comparison"]=timing
    print(json.dumps({"source":"CLEAN real HTTPS CSV/official adapter","day":day,"evidence":evidence},ensure_ascii=False))
if __name__=="__main__":
    main(sys.argv[1] if len(sys.argv)>1 else None)
