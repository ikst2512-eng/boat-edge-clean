#!/usr/bin/env python3
"""Research-only 92-day official K postrace 2C / course-attack description.

Uses existing research_official_k_one_day_compare.parse_k/unpack_lha.
Never imports the forecast engine; no T-12 / production use or causal claim.
"""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import date, timedelta
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

if __package__:
    from .research_official_k_one_day_compare import RACE, parse_k, unpack_lha
else:
    from research_official_k_one_day_compare import RACE, parse_k, unpack_lha

EXPECTED_ARTIFACT_SHA256 = "c668f545bae54f8148616315e307ed2a2b04a77a0cb8abf88bf3ea078749ce8e"
EXPECTED_ARTIFACT_BYTES = 3398466
EXCLUDED = {"F", "S0", "S1", "S2"}

def verify_original_zip(artifact_zip: Path):
    """Pin entire original Actions ZIP independently from its enclosed manifest."""
    if artifact_zip.is_symlink() or not artifact_zip.is_file():
        raise ValueError("official_K_artifact_missing_or_symlink")
    if artifact_zip.stat().st_size != EXPECTED_ARTIFACT_BYTES:
        raise ValueError("official_K_artifact_size_not_frozen")
    h = hashlib.sha256()
    with artifact_zip.open("rb") as inp:
        for chunk in iter(lambda: inp.read(1024 * 1024), b""):
            h.update(chunk)
    digest = h.hexdigest()
    if digest != EXPECTED_ARTIFACT_SHA256:
        raise ValueError("official_K_artifact_SHA_does_not_match_independent_receipt")
    return digest
BANDS = ("0-2m", "3-4m", "5m+")
FIELDS = ("c1_escapement", "c1_win", "c2_sashi", "c2_win",
          "c3_makuri", "c4_makuri", "c3_makurizashi", "c4_makurizashi")

def wind_bin(m):
    if not isinstance(m, int) or m < 0:
        raise ValueError("invalid_postrace_wind")
    return "0-2m" if m <= 2 else "3-4m" if m <= 4 else "5m+"

def race_outcome(r):
    """Return None if any required course/1C/2C result condition fails."""
    entries = r["entries"]
    actual = {e["course"]: e for e in entries if e["course"] is not None}
    if len(actual) != 6 or set(actual) != set(range(1, 7)):
        return None
    c1, c2 = actual[1], actual[2]
    if c1["status"] in EXCLUDED or c2["status"] in EXCLUDED or r.get("unsettled"):
        return None
    win = [e for e in entries if e["status"] == "01"]
    if len(win) != 1:
        raise ValueError("eligible_winner_not_unique")
    w = win[0]
    method = r["method"]
    return {
        "c1_win": int(c1["status"] == "01"),
        "c1_escapement": int(c1["status"] == "01" and method == "逃げ"),
        "c2_win": int(c2["status"] == "01"),
        "c2_sashi": int(c2["status"] == "01" and method == "差し"),
        "c3_makuri": int(w["course"] == 3 and method == "まくり"),
        "c4_makuri": int(w["course"] == 4 and method == "まくり"),
        "c3_makurizashi": int(w["course"] == 3 and method == "まくり差し"),
        "c4_makurizashi": int(w["course"] == 4 and method == "まくり差し"),
    }

def public_counts(counter):
    n = counter["eligible"]
    return {"eligible": n, **{
        k: {"count": counter[k], "percent": round(counter[k] * 100/n, 4) if n else None}
        for k in FIELDS
    }}

def analyze(artifact_zip: Path):
    expected_dates = [(date(2026, 8, 1) + timedelta(days=i)).strftime("%Y%m%d") for i in range(92)]
    totals, by_wind = Counter(), {b: Counter() for b in BANDS}
    by_venue = {f"{n:02d}": Counter() for n in range(1,25)}
    by_venue_month_wind = {
        f"{n:02d}": {m: {b: Counter() for b in BANDS} for m in ("08", "09", "10")}
        for n in range(1,25)
    }
    sha_rows = []
    raw_n = known_c1_n = known_c1_wins = 0
    pinned_sha256 = verify_original_zip(artifact_zip)
    with ZipFile(artifact_zip) as z:
        if z.testzip() is not None:
            raise ValueError("source_artifact_ZIP_CRC_failed")
        manifest = json.loads(z.read("official_k_full_92day_reconciliation.json"))
        if manifest.get("study_period") != "2026-08-01/2026-10-31":
            raise ValueError("not_fixed_92day_source_period")
        per_day = {r["day"]: r for r in manifest["results"]}
        if set(per_day) != set(expected_dates) or len(manifest["results"]) != 92:
            raise ValueError("official_K_days_missing")
        for day in expected_dates:
            frozen = per_day[day]
            raw = z.read("official_k_full_92_raw/k" + day[2:] + ".lzh")
            sha = hashlib.sha256(raw).hexdigest()
            if sha != frozen["official_K_sha256"]:
                raise ValueError("official_K_source_SHA_failed:" + day)
            decoded = unpack_lha(raw, day=day)
            decode_sha = hashlib.sha256(decoded).hexdigest()
            if decode_sha != frozen["decoded_sha256"]:
                raise ValueError("official_K_decoded_SHA_failed:" + day)
            txt = decoded.decode("cp932")
            expected_races = sum(bool(RACE.match(line)) for line in txt.splitlines())
            races = parse_k(txt, day=day, expected_races=expected_races, allow_unsettled=True)
            if len(races) != frozen["official_K_races"]:
                raise ValueError("official_K_race_count_failed:" + day)
            sha_rows.append({"day": day, "raw_sha256": sha, "decoded_sha256": decode_sha})
            raw_n += len(races)
            for r in races.values():
                actual = [e for e in r["entries"] if e["course"] == 1]
                if len(actual) == 1 and actual[0]["status"] not in EXCLUDED:
                    known_c1_n += 1
                    known_c1_wins += int(actual[0]["status"] == "01")
                outcome = race_outcome(r)
                if outcome is None:
                    continue
                venue, month, band = r["venue"], day[4:6], wind_bin(r["wind_m"])
                if venue not in by_venue:
                    raise ValueError("venue_out_of_range:" + venue)
                for counter in (totals, by_wind[band], by_venue[venue],
                                by_venue_month_wind[venue][month][band]):
                    counter["eligible"] += 1
                    counter.update(outcome)
    if (raw_n, known_c1_n, known_c1_wins) != (14249, 14090, 7811):
        raise ValueError("baseline_C1_official_K_reproduction_failed")
    if totals["eligible"] != 13815:
        raise ValueError("comparison_universe_changed_expected_13815")
    return {
        "schema": "BOAT_EDGE_OFFICIAL_K_C2_ESCAPE_POSTRACE_V1",
        "period": "2026-08-01/2026-10-31",
        "classification": "official_primary_postrace_descriptive_only_not_T12",
        "source": {"artifact_id": 13607470249, "zip_sha256": pinned_sha256, "raw_races": raw_n, "sha_verified_days": len(sha_rows),
                   "prior_C1_valid": known_c1_n, "prior_C1_wins": known_c1_wins},
        "definitions": {
            "eligible": "six distinct actual course entrants, C1/C2 statuses not F/S0/S1/S2, settled winner",
            "c1_escapement": "actual C1 wins with result method 逃げ / eligible; not official player-specific C2 逃がし率 or a validated wall predictor",
            "c2_sashi": "actual C2 wins with result method 差し / eligible; not method composition among C2 wins",
            "all_wind": "official K postrace wind only; forbidden in same-race predeadline prediction",
        },
        "national": public_counts(totals),
        "by_postrace_wind": {b: public_counts(c) for b,c in by_wind.items()},
        "by_venue": {v:public_counts(c) for v,c in by_venue.items()},
        "by_venue_month_wind": {v:{m:{b:public_counts(c) for b,c in bins.items()}
                                    for m,bins in months.items()}
                                for v,months in by_venue_month_wind.items()},
        "source_daily_sha": sha_rows,
        "t12_eligible": False,
        "proven_forecast_improvement": False,
        "model_approval": False,
    }

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--artifact-zip", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    args=p.parse_args()
    result=analyze(args.artifact_zip)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"official_K_races":result["source"]["raw_races"],
                      "eligible":result["national"]["eligible"],
                      "approved":result["model_approval"]},ensure_ascii=False))
if __name__=="__main__":
    main()
