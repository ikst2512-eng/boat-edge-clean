#!/usr/bin/env python3
"""#1692: research-only 2C wall/exhibition + observation-time evidence bridge.

Read the two *already captured* Nov 9/10 official beforeinfo/odds ZIPs.
Reuse #1694 source observations, never collect new races or claim T-12
three-source/model/forecast certification. No model, UI or cron imports.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import re
from zipfile import ZipFile

OFFICIAL_SOURCES = {
    "20261109": {
        "zip_sha256": "99f02ff306307dd945f27c225e18ff8341be2832232b7dd0f2751e1d8935f451",
        "zip_bytes": 28063, "run_id": 42567310743,
        "artifact_id": 13652131213, "prefix": "before_run42567310743",
        "odds_prefix": "odds_run42567310743",
        "race_codes": ("202611091110", "202611091710"),
    },
    "20261110": {
        "zip_sha256": "cdfdeae53222a5b7852ba5cf5b6b44080247ec074c8d3dbaf53c4a32fe9706dd",
        "zip_bytes": 32936, "run_id": 42769768447,
        "artifact_id": 13740574410, "prefix": "before_run42769768447",
        "odds_prefix": "odds_run42769768447",
        "race_codes": ("202611101202", "202611102211"),
    },
}

def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def parse_st(raw):
    """Parse ONLY a valid 0.xx exhibition ST as a descriptive number."""
    if not isinstance(raw, str) or not re.fullmatch(r"\.\d{2}", raw):
        return None
    value = Decimal(raw)
    if value < 0 or value >= 1:
        return None
    return value

def measure_race_label(label: object, rno: int) -> dict:
    """Measuretime is a prior-RACE LABEL, never an actual timestamp."""
    result={"raw_label":label if isinstance(label,str) else None,
            "source_race_number":None, "race_number_gap":None,
            "same_target_race":False, "actual_measurement_timestamp":None,
            "measurement_timestamp_verified":False}
    match=re.fullmatch(r"(\d{1,2})R時点",label) if isinstance(label,str) else None
    if not match:
        return result
    source=int(match.group(1))
    if not 1<=source<=12:
        return result
    result["source_race_number"]=source
    result["race_number_gap"]=rno-source if rno>=source else None
    result["same_target_race"]=rno==source
    return result

def summarize_exhibition(items: object) -> dict:
    out={"course_to_boat":None,"course_st_seconds":None,
         "complete_six_course_ST":False,
         "c2_minus_c3_ST_seconds":None,"c2_minus_c4_ST_seconds":None,
         "wall_performance_proven":False}
    if not isinstance(items,list) or len(items)!=6:
        return out
    boats,courses,st={}, {}, {}
    for row in items:
        if not isinstance(row,dict):
            return out
        try:
            course=int(row["cs"]);boat=int(row["teino"])
        except (ValueError,TypeError,KeyError):
            return out
        val=parse_st(row.get("st"))
        if course in courses or boat in boats or val is None:
            return out
        courses[course]=boat;boats[boat]=course;st[course]=val
    if set(courses)!=set(range(1,7)) or set(boats)!=set(range(1,7)):
        return out
    out["course_to_boat"]={str(i):courses[i] for i in range(1,7)}
    out["course_st_seconds"]={str(i):str(st[i]) for i in range(1,7)}
    out["complete_six_course_ST"]=True
    out["c2_minus_c3_ST_seconds"]=str(st[2]-st[3])
    out["c2_minus_c4_ST_seconds"]=str(st[2]-st[4])
    return out

def replay_archive(path: Path, day: str) -> list[dict]:
    frozen=OFFICIAL_SOURCES[day]
    if path.is_symlink() or not path.is_file():
        raise ValueError("original_zip_missing_or_symlink:"+day)
    raw=path.read_bytes()
    if len(raw)!=frozen["zip_bytes"] or digest(raw)!=frozen["zip_sha256"]:
        raise ValueError("original_zip_independent_SHA_or_length_mismatch:"+day)
    rows=[]
    with ZipFile(path) as z:
        if z.testzip() is not None:
            raise ValueError("original_zip_CRC_failed:"+day)
        allfiles=set(z.namelist())
        if len(allfiles)!=len(z.namelist()):
            raise ValueError("duplicate_zip_path")
        for race_code in frozen["race_codes"]:
            beforebase=("official_joint_evidence/observations/"
                        +frozen["prefix"]+"/"+day+"/"+race_code)
            oddsbase=("official_joint_evidence/observations/"
                      +frozen["odds_prefix"]+"/"+day+"/"+race_code)
            required=(beforebase+"/beforeinfo.json",beforebase+"/manifest.json",
                      oddsbase+"/original.html",oddsbase+"/manifest.json")
            if not set(required).issubset(allfiles):
                raise ValueError("missing_pair_source:"+race_code)
            beforebytes=z.read(required[0]); b=json.loads(beforebytes)
            before_manifest=json.loads(z.read(required[1]))
            oddsbytes=z.read(required[2]); odds_manifest=json.loads(z.read(required[3]))
            for payload, meta, source in ((beforebytes,before_manifest,"beforeinfo"),
                                           (oddsbytes,odds_manifest,"odds")):
                if meta.get("race_code")!=race_code or meta.get("sha256")!=digest(payload) or meta.get("bytes")!=len(payload):
                    raise ValueError("source_manifest_byte_mismatch:"+race_code+":"+source)
            race=b.get("maindata",{})
            if (str(race.get("jcd")) != race_code[8:10] or
                int(race.get("rno") or -1) != int(race_code[10:12]) or
                str(race.get("hd")) != day):
                raise ValueError("beforeinfo_race_key_mismatch:"+race_code)
            rno=int(race_code[10:12])
            exhibition=summarize_exhibition(race.get("sttenjiinfolist"))
            deadline=datetime.fromisoformat(day[:4]+"-"+day[4:6]+"-"+day[6:8]+"T"+race["deadline"]+":00+09:00")
            cutoff=deadline-timedelta(minutes=12)
            received=datetime.fromisoformat(before_manifest["received_at_jst"])
            oddsreceived=datetime.fromisoformat(odds_manifest["received_at_jst"])
            if not (received.tzinfo and oddsreceived.tzinfo):
                raise ValueError("unaware_receipt_clock")
            if (int(before_manifest.get("racers_listed",-1))!=6 or
                len(race.get("teiinfolist",[]))!=6):
                raise ValueError("six_boat_original_missing")
            if (exhibition["complete_six_course_ST"] != bool(
                before_manifest.get("start_exhibition_six_valid_rows"))):
                raise ValueError("exhibition_manifest_replay_conflict:"+race_code)
            weather=race.get("weatherinfo",{})
            observation=measure_race_label(weather.get("measuretime"),rno)
            # Do not interpret undocumented northdirec/winddirec as geographical
            # FROM/TO directions or assert the time of actual weather sampling.
            row={
                "race_code":race_code,
                "venue_code":race_code[8:10],
                "race_number":rno,
                "deadline_jst":deadline.isoformat(),
                "t12_cutoff_jst":cutoff.isoformat(),
                "beforeinfo_received_jst_collector_claim":received.isoformat(),
                "odds_received_jst_collector_claim":oddsreceived.isoformat(),
                "both_receipts_before_t12_collector_claim":received<=cutoff and oddsreceived<=cutoff,
                "source_github_artifact_id":frozen["artifact_id"],
                "source_zip_sha256":frozen["zip_sha256"],
                "beforeinfo_sha256":digest(beforebytes),
                "odds_original_sha256":digest(oddsbytes),
                "odds_120_reported_by_existing_source_auditor":odds_manifest.get("valid_120_combinations") is True and odds_manifest.get("odds_entries")==120,
                "exhibition":exhibition,
                "weather":{
                    "wind_m_raw":weather.get("wind"),
                    "wave_cm_raw":weather.get("wave"),
                    "northdirec_code_uninterpreted":weather.get("northdirec"),
                    "winddirec_code_uninterpreted":weather.get("winddirec"),
                    "observation_provenance":observation,
                    "official_wind_FROM_TO_verified":False,
                    "relative_wind_usable":False,
                },
                "same_race_racelist_original_verified":False,
                "same_race_official_final_entry_verified":False,
                "source_consumed_by_new_forecast_proven":False,
                "first_forecast_remote_acceptance_proven":False,
                "formal_T12_certified":False,
                "predictive_wall_effect_proven":False,
                "approved_for_production":False,
            }
            rows.append(row)
    return rows

def analyze(nov9: Path,nov10: Path) -> dict:
    rows=replay_archive(nov9,"20261109")+replay_archive(nov10,"20261110")
    if [r["race_code"] for r in rows] != [
        "202611091110","202611091710","202611101202","202611102211"]:
        raise ValueError("fixed_four_race_universe_changed")
    ncomplete=sum(r["exhibition"]["complete_six_course_ST"] for r in rows)
    prior_weather=sum((r["weather"]["observation_provenance"]["race_number_gap"] or 0)>0 for r in rows)
    if ncomplete!=3 or prior_weather!=4:
        raise ValueError("source_feature_status_changed_fail_closed")
    if not all(r["both_receipts_before_t12_collector_claim"] for r in rows):
        raise ValueError("receipt_self_clock_status_drift")
    return {
        "schema":"BOAT_EDGE_RESEARCH_OFFICIAL_BEFOREINFO_2C_WALL_OBSERVATION_V1",
        "provenance":"two existing official beforeinfo+odds original ZIPs, sha-frozen; no new HTTP collector",
        "scope":"4 fixed historical races across Nov 9-10; not representative or any production model cohort",
        "source_zip_sha256_by_day":{day:a["zip_sha256"] for day,a in OFFICIAL_SOURCES.items()},
        "counts":{"fixed_races":len(rows),"source_raw_zip_sha_verified":2,
                  "raw_beforeinfo_and_odds_pair_sha_verified":4,
                  "six_boat_exhibition_course_ST_complete":ncomplete,
                  "weather_measure_race_label_earlier_than_target":prior_weather,
                  "official_wind_arrow_FROM_TO_verified":0,
                  "same_race_racelist_originals":0,
                  "source_consumed_by_new_forecast":0,
                  "independent_first_forecast_remote_acceptance":0,
                  "formal_T12_certified":0,
                  "forecast_effect_proven":0},
        "observations":rows,
        "research_descriptive_only":True,
        "production_change_allowed":False,
    }

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--nov9-zip",type=Path,required=True)
    p.add_argument("--nov10-zip",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    data=analyze(args.nov9_zip,args.nov10_zip)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(data["counts"],sort_keys=True))

if __name__=="__main__":
    main()
