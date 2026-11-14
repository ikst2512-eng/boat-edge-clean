"""Pinned official-K course method rates, research only.

Uses frozen #1692 parser and original 92-day ZIP. Correct denominators:
- C2 escape-assist: eligible C1/C2 actual-course pairs (not a causal wall).
- C3/C4 makuri and makuri-sashi: STRICT six-numeric-finisher cohort only.
The latter is NOT all course starts; do not label it official athlete win
method rate or inject into a forecast's actual_course_starts field.
Aug/Sep is train; October is a separate historical diagnostic cohort.
Target race is not accessed for any result. This module creates NO ticket.
"""
from collections import Counter, defaultdict
from datetime import date, timedelta
from hashlib import sha256
from pathlib import Path
from zipfile import ZipFile
import json
import re

from scenario_official_K_attack_benefit_holdout import _record, _wilson

STUDY="RETROSPECTIVE_ONLY_K92_C2_ESCAPE_C3C4_METHOD_BY_ATHLETE_V1"
ORIGINAL_K_SHA="c668f545bae54f8148616315e307ed2a2b04a77a0cb8abf88bf3ea078749ce8e"
EXPECTED=(14249,13815,13301,9241,4574,8919,4382)
REG=re.compile(r"[0-9]{4}\Z")
TARGET=re.compile(r"20[0-9]{10}\Z")
METHODS=("まくり","まくり差し")
MIN_DESCRIPTIVE_SAMPLE=30


def _safe_summary(counter, prefix, denom):
    n=counter[denom]
    return {
        "eligible_starts":n,
        "not_all_course_starts":prefix=="method_",
        **{method:{
            "wins":counter[prefix+method],
            "rate_pct":round(100*counter[prefix+method]/n,4) if n else None,
            "wilson_95_pct":_wilson(counter[prefix+method],n)["wilson_95_pct"],
            "small_sample_n_below_30":n<MIN_DESCRIPTIVE_SAMPLE,
            "forecast_rate_allowed":False,
        } for method in METHODS},
        "source_denominator":("complete_six_numeric_finishers_by_actual_course"
                              if prefix=="method_" else
                              "K92_eligible_actual_C1_C2_pairs"),
    }


def analyze_k_method_athlete(zip_path, target_race, exhibition_roster):
    """Never infer final target course from its exhibition course."""
    if (type(target_race) is not str or not TARGET.fullmatch(target_race)
            or target_race[:8]<="20261031"
            or type(exhibition_roster) is not list or len(exhibition_roster)!=6):
        raise ValueError("K92_target_and_six_exhibition_roster_required")
    try:
        target_day=date.fromisoformat(
            target_race[:4]+"-"+target_race[4:6]+"-"+target_race[6:8])
    except ValueError as e:
        raise ValueError("K92_target_date_invalid") from e
    if target_day<=date(2026,10,31):
        raise ValueError("K92_history_not_before_target")
    for i, row in enumerate(exhibition_roster,1):
        if (type(row) is not dict or
                set(row)!={"boat","registration","exhibition_course"} or
                type(row["boat"]) is not int or row["boat"]!=i or
                type(row["registration"]) is not str or
                not REG.fullmatch(row["registration"]) or
                type(row["exhibition_course"]) is not int):
            raise ValueError("K92_six_boat_roster_contract")
    if (len({v["registration"] for v in exhibition_roster})!=6 or
            {v["exhibition_course"] for v in exhibition_roster}!=set(range(1,7)) or
            not 1<=int(target_race[8:10])<=24 or
            not 1<=int(target_race[10:12])<=12):
        raise ValueError("K92_exhibition_permutation_identity_invalid")

    # Delayed import: original source parser is independently blob pinned in
    # #1710 CI; this function cannot attest its identity or first receipt.
    from research_official_k_c2_escape_conditional_92day import (
        verify_original_zip, race_outcome)
    from research_official_k_one_day_compare import RACE, parse_k, unpack_lha

    path=Path(zip_path)
    digest=verify_original_zip(path)
    if digest!=ORIGINAL_K_SHA:
        raise ValueError("K92_primary_sha_changed")
    c2=defaultdict(Counter)
    c34=defaultdict(Counter)
    by_period={
        "aug_sep_training":{"c2":Counter(),"c3":Counter(),"c4":Counter()},
        "october_historical_holdout":{"c2":Counter(),"c3":Counter(),"c4":Counter()},
    }
    counts=Counter()
    original_daily=[]
    days=[(date(2026,8,1)+timedelta(days=i)).strftime("%Y%m%d") for i in range(92)]
    with ZipFile(path) as archive:
        if archive.testzip() is not None or len(set(archive.namelist()))!=len(archive.namelist()):
            raise ValueError("K92_zip_crc_or_duplicate")
        manifest=json.loads(archive.read("official_k_full_92day_reconciliation.json"))
        if manifest.get("study_period")!="2026-08-01/2026-10-31":
            raise ValueError("K92_study_period_drift")
        entries=manifest.get("results")
        if (type(entries) is not list or len(entries)!=92
                or len({entry.get("day") for entry in entries})!=92):
            raise ValueError("K92_manifest_dates_invalid")
        by_day={entry["day"]:entry for entry in entries}
        if set(by_day)!=set(days):
            raise ValueError("K92_day_coverage_drift")
        for day in days:
            raw=archive.read("official_k_full_92_raw/k"+day[2:]+".lzh")
            orig_hash=sha256(raw).hexdigest()
            if orig_hash!=by_day[day]["official_K_sha256"]:
                raise ValueError("K92_daily_original_sha_drift:"+day)
            decoded=unpack_lha(raw,day=day)
            deco_hash=sha256(decoded).hexdigest()
            if deco_hash!=by_day[day]["decoded_sha256"]:
                raise ValueError("K92_daily_decoded_sha_drift:"+day)
            original_daily.append((day,orig_hash,deco_hash))
            raw_text=decoded.decode("cp932")
            expected_races=sum(bool(RACE.match(line)) for line in raw_text.splitlines())
            races=parse_k(raw_text,day=day,expected_races=expected_races,
                          allow_unsettled=True)
            if len(races)!=by_day[day]["official_K_races"]:
                raise ValueError("K92_daily_race_count_drift:"+day)
            cohort=("aug_sep_training" if day[4:6] in ("08","09")
                    else "october_historical_holdout")
            counts["raw"]+=len(races)
            for race in races.values():
                result=race_outcome(race)
                if result is None:
                    continue
                counts["c2"]+=1
                counts["c2_"+cohort]+=1
                actual={v["course"]:v for v in race["entries"]
                        if v.get("course") is not None}
                if set(actual)!=set(range(1,7)):
                    raise ValueError("K92_actual_six_course_drift")
                registrations=[v.get("athlete_registration") for v in actual.values()]
                if (len(set(registrations))!=6 or
                        any(type(reg) is not str or not REG.fullmatch(reg)
                            for reg in registrations)):
                    raise ValueError("K92_athlete_identity_drift")
                reg2=actual[2]["athlete_registration"]
                yes=result["c1_escapement"]
                counter=c2[(cohort,reg2)]
                counter["eligible"]+=1
                counter["escape"]+=yes
                by_period[cohort]["c2"]["eligible"]+=1
                by_period[cohort]["c2"]["escape"]+=yes

                clean=_record(race)
                if clean is None:
                    continue
                counts["clean"]+=1
                counts["clean_"+cohort]+=1
                winner_course=clean["first_course"]
                method=clean["method"]
                for course in (3,4):
                    reg=actual[course]["athlete_registration"]
                    target=c34[(cohort,course,reg)]
                    target["eligible"]+=1
                    by_period[cohort]["c"+str(course)]["eligible"]+=1
                    if winner_course==course and method in METHODS:
                        key="method_"+method
                        target[key]+=1
                        by_period[cohort]["c"+str(course)][key]+=1

    observed=tuple(counts[k] for k in (
        "raw","c2","clean","c2_aug_sep_training",
        "c2_october_historical_holdout",
        "clean_aug_sep_training","clean_october_historical_holdout"))
    if observed!=EXPECTED:
        raise ValueError("K92_official_cohort_invariants_changed:"+str(observed))
    course_lookup={r["exhibition_course"]:r for r in exhibition_roster}
    c2row=course_lookup[2]
    matched_c2={}
    for cohort in by_period:
        a=c2[(cohort,c2row["registration"])]
        n=a["eligible"]
        matched_c2[cohort]={
            "registration":c2row["registration"],
            "eligible_C2_pair_starts":n,
            "C1_escape_while_athlete_C2":a["escape"],
            "historical_C2_escape_assist_pct":round(100*a["escape"]/n,4) if n else None,
            "wilson_95_pct":_wilson(a["escape"],n)["wilson_95_pct"],
            "small_sample_n_below_30":n<MIN_DESCRIPTIVE_SAMPLE,
            "forecast_rate_allowed":False,
            "not_verified_vendor_C2_escape_rate":True,
        }
    matched_methods={}
    for course in (3,4):
        target=course_lookup[course]
        matched_methods[str(course)]={
            "registration":target["registration"],
            "exhibition_course_only":course,
            **{cohort:_safe_summary(c34[(cohort,course,target["registration"])],
                                   "method_","eligible")
               for cohort in by_period},
        }
    national={
        cohort:{
            "C2_eligible_pairs":{
                "eligible":by_period[cohort]["c2"]["eligible"],
                "C1_escape":by_period[cohort]["c2"]["escape"],
            },
            **{f"C{course}_complete_six_finishers":
                _safe_summary(by_period[cohort]["c"+str(course)],
                              "method_","eligible")
               for course in (3,4)},
        } for cohort in by_period
    }
    return {
        "schema":STUDY,
        "target_race":target_race,
        "source_zip_sha256":digest,
        "daily_sha_fingerprint_sha256":sha256(
            json.dumps(original_daily,separators=(",",":")).encode()).hexdigest(),
        "verified_92_original_K_days":len(original_daily),
        "raw_races":counts["raw"],
        "eligible_C1_C2_pair_races":counts["c2"],
        "complete_six_numeric_finishers":counts["clean"],
        "national_historical_only":national,
        "joined_real_exhibition_course2":matched_c2,
        "joined_real_exhibition_course3_4":matched_methods,
        "october_labels_used_in_aug_sep_training":False,
        "future_actual_entry_not_verified":True,
        "not_all_course_starts_denominator":True,
        "motor_comment_other_attack_signals_not_observed":True,
        "K92_historical_results_not_live_same_race":True,
        "source_receiver_first_remote_clock_verified":False,
        "use_as_predeadline_model_rate_allowed":False,
        "model_predictions_generated":False,
        "model_coefficients_changed":False,
        "production_changed":False,
        "formal":False,
    }
