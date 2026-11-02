"""Run bounded, reproducible historical four-mode research on real archived files."""
import json
import re
from pathlib import Path
from four_mode_research_batch import summarize, MODES

ROOT = Path(__file__).resolve().parent

def summarize_group(codes, root):
    # summarize accepts max 30 codes; keep every subgroup bounded.
    chunks = [summarize(codes[i:i+30], root=root) for i in range(0, len(codes), 30)]
    comparable = sum(x["historical_comparable"] for x in chunks)
    hits = {m: {f"top{n}": sum(x["modes"][m]["topn_hits"][f"top{n}"] for x in chunks)
                for n in (3,5,10)} for m in MODES}
    return {"requested": len(codes), "historical_comparable": comparable,
            "topn_hits": hits, "formal": False}


def run(root=ROOT, limit=120):
    root = Path(root)
    forecast_dir, results_dir = root / "four_mode_forecasts", root / "confirmed_results"
    available = sorted(p.stem for p in forecast_dir.glob("20??????????.json")
                       if re.fullmatch(r"20[0-9]{10}", p.stem)
                       and (results_dir / p.name).is_file())
    # Rotate through both dates and venues, avoiding early venue/race-order bias.
    # All choices are deterministic and based only on immutable filenames.
    by_day_venue = {}
    for code in available:
        by_day_venue.setdefault(code[:8], {}).setdefault(code[8:10], []).append(code)
    by_date = {}
    for day, venues in by_day_venue.items():
        selected = []
        offset = 0
        while True:
            batch = [venues[venue][offset] for venue in sorted(venues)
                     if offset < len(venues[venue])]
            if not batch:
                break
            selected.extend(batch)
            offset += 1
        by_date[day] = selected
    codes = []
    day_keys = sorted(by_date)
    offset = 0
    while len(codes) < limit:
        batch = [by_date[day][offset] for day in day_keys if offset < len(by_date[day])]
        if not batch:
            break
        codes.extend(batch[:limit - len(codes)])
        offset += 1
    if not codes:
        return {"status": "no_paired_archives", "formal": False, "requested": 0}
    overall = summarize_group(codes, root)
    codes.sort()
    days = sorted(set(code[:8] for code in codes))
    venues = sorted(set(code[8:10] for code in codes))
    return {"status": "historical_research_only", "cohort_codes": codes,
            **overall, "by_day": {day: summarize_group([c for c in codes if c[:8] == day], root) for day in days},
            "by_venue_code": {venue: summarize_group([c for c in codes if c[8:10] == venue], root) for venue in venues},
            "warning": "Selected earliest matching archives only. Historical coverage; not prospective proof."}

if __name__ == "__main__":
    report = run()
    output = Path("four_mode_historical_cohort_report.json")
    output.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + chr(10), encoding="utf-8")
    print("HISTORICAL_FOUR_MODE_COHORT=" + json.dumps({
        "status": report["status"],
        "requested": report["requested"],
        "comparable": report.get("historical_comparable"),
        "topn": report.get("topn_hits", {}),
        "by_day": report.get("by_day", {}),
        "by_venue_code": report.get("by_venue_code", {})}, ensure_ascii=False, sort_keys=True))
