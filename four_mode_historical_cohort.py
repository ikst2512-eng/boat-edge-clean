"""Run bounded, reproducible historical four-mode research on real archived files."""
import json
import re
from pathlib import Path
from four_mode_research_batch import summarize

ROOT = Path(__file__).resolve().parent

def run(root=ROOT, limit=30):
    root = Path(root)
    forecast_dir, results_dir = root / "four_mode_forecasts", root / "confirmed_results"
    codes = sorted(p.stem for p in forecast_dir.glob("20??????????.json")
                   if re.fullmatch(r"20[0-9]{10}", p.stem)
                   and (results_dir / p.name).is_file())[:limit]
    if not codes:
        return {"status": "no_paired_archives", "formal": False, "requested": 0}
    out = summarize(codes, root=root)
    return {"status": "historical_research_only", "cohort_codes": codes, **out}

if __name__ == "__main__":
    report = run()
    output = Path("four_mode_historical_cohort_report.json")
    output.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + chr(10), encoding="utf-8")
    print("HISTORICAL_FOUR_MODE_COHORT=" + json.dumps({
        "status": report["status"],
        "requested": report["requested"],
        "comparable": report.get("historical_comparable"),
        "topn": {mode: row["topn_hits"] for mode, row in report.get("modes", {}).items()},
        "paired": report.get("paired_top10", {})}, ensure_ascii=False, sort_keys=True))
