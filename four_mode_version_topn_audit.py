"""Read-only historical TopN audit stratified by frozen model version and date.

This never asserts prospective validity, nor alters forecast archives.
"""
import json
from collections import defaultdict
from pathlib import Path

from four_mode_historical_cohort import ROOT, run
from four_mode_frozen_diagnostic import compare_race
from four_mode_research_batch import MODES

TOPS = (3, 5, 10)


def analyze(root=ROOT, limit=120):
    root = Path(root)
    cohort = run(root=root, limit=limit)
    if cohort.get("status") != "historical_research_only":
        return {"status": "no_eligible_archives", "formal": False, "groups": {}}
    buckets = defaultdict(list)
    excluded = []
    for code in cohort["cohort_codes"]:
        path = root / "four_mode_forecasts" / (code + ".json")
        row = compare_race(code, root)
        if row.get("status") != "historical_comparison_only":
            excluded.append({"code": code, "reason": row.get("status")})
            continue
        try:
            if path.is_symlink() or path.stat().st_size > 30000:
                raise ValueError("unsafe_forecast")
            record = json.loads(path.read_text(encoding="utf-8"))
            version = record["model_version"]
            if not isinstance(version, str) or not version.startswith("CLEAN_FOUR_MODES_V"):
                raise ValueError("invalid_model_version")
            if any(type(row["modes"][m][f"top{n}"]) is not bool
                   for m in MODES for n in TOPS):
                raise ValueError("invalid_topn")
        except (KeyError, ValueError, OSError, TypeError):
            excluded.append({"code": code, "reason": "invalid_version_or_topn"})
            continue
        buckets[(version, code[:8])].append(row)
    groups = {}
    for (version, day), rows in sorted(buckets.items()):
        counts = {m: {f"top{n}": sum(bool(r["modes"][m][f"top{n}"]) for r in rows)
                      for n in TOPS} for m in MODES}
        groups.setdefault(version, {})[day] = {
            "evaluated": len(rows), "topn_hits": counts,
            "topn_pct": {m: {f"top{n}": round(100 * counts[m][f"top{n}"] / len(rows), 2)
                              for n in TOPS} for m in MODES},
            "formal": False}
    return {"status": "historical_version_stratified",
            "formal": False, "independent_predeadline_proof": False,
            "requested": cohort["requested"],
            "evaluated": sum(len(v) for v in buckets.values()),
            "excluded": excluded, "groups": groups,
            "warning": "Do not pool V1/V2 or promote to official accuracy; dates are descriptive, not independent holdouts."}


if __name__ == "__main__":
    report = analyze()
    print("VERSION_STRATIFIED_TOPN=" + json.dumps(report, ensure_ascii=False, sort_keys=True))
