"""Read-only official beforeinfo JSON readiness inspection.

Six listed racers are NOT proof that exhibition readings exist. No formal
T-12 eligibility is inferred from an undated archived JSON response.
"""
import argparse
import json
from pathlib import Path


def inspect(payload):
    if not isinstance(payload, dict):
        raise ValueError("official JSON root must be an object")
    main = payload.get("maindata")
    if not isinstance(main, dict):
        raise ValueError("missing official maindata")
    racers = main.get("teiinfolist")
    if not isinstance(racers, list):
        raise ValueError("missing official teiinfolist")
    ids = [v.get("teino") if isinstance(v, dict) else None for v in racers]
    unique_six = len(ids) == 6 and set(ids) == set("123456")
    exhibition = unique_six and all(
        isinstance(v.get("extime"), (str, int, float))
        and str(v["extime"]).strip() not in ("", "-")
        for v in racers
    )
    start = main.get("sttenjiinfolist")
    return {
        "race_number": str(main.get("rno", "")),
        "deadline_display": main.get("deadline"),
        "racers_listed": len(racers),
        "six_unique_boats": unique_six,
        "exhibition_time_nonempty_six": bool(exhibition),
        "start_exhibition_rows": len(start) if isinstance(start, list) else None,
        "status": "six_exhibition_values_observed_not_time_certified" if exhibition
                  else "official_racecard_without_complete_exhibition_values",
        "t12_eligible": False,
        "forecast_usable": False,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("file")
    args = parser.parse_args()
    print(json.dumps(inspect(json.loads(Path(args.file).read_text(encoding="utf-8"))),
                     ensure_ascii=False, indent=2))
