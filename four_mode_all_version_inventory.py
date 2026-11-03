"""Read-only exhaustive inventory before bounded TopN cohort selection."""
import json
import re
from collections import defaultdict
from pathlib import Path

from four_mode_frozen_diagnostic import compare_race
from four_mode_research_batch import MODES

ROOT = Path(__file__).resolve().parent
TOPS = (3, 5, 10)


def inventory(root=ROOT):
    root = Path(root)
    forecast_dir = root / "four_mode_forecasts"
    results_dir = root / "confirmed_results"
    counts = defaultdict(lambda: {"forecast_files": 0, "paired_results": 0,
                                  "comparable": 0,
                                  "topn_hits": {m: {f"top{n}": 0 for n in TOPS} for m in MODES}})
    rejected = defaultdict(int)
    if not forecast_dir.is_dir():
        return {"status": "archive_directory_missing", "formal": False, "groups": {},
                "rejections": {}}
    for path in sorted(forecast_dir.glob("*.json")):
        code = path.stem
        if not re.fullmatch(r"20[0-9]{10}", code):
            continue
        try:
            if path.is_symlink() or path.stat().st_size > 30000:
                raise ValueError("unsafe_file")
            obj = json.loads(path.read_text(encoding="utf-8"))
            version = obj.get("model_version")
            if (obj.get("race_code") != code or not isinstance(version, str)
                    or not re.fullmatch(r"CLEAN_FOUR_MODES_V[0-9]+_[A-Z0-9_]+", version)):
                raise ValueError("bad_version_or_identity")
        except (OSError, ValueError, TypeError):
            rejected["invalid_forecast_or_version"] += 1
            continue
        group = counts[(version, code[:8])]
        group["forecast_files"] += 1
        result_path = results_dir / path.name
        if result_path.is_symlink() or not result_path.is_file():
            continue
        group["paired_results"] += 1
        comparison = compare_race(code, root)
        if comparison.get("status") != "historical_comparison_only":
            rejected["invalid_comparison"] += 1
            continue
        try:
            for m in MODES:
                flags = [comparison["modes"][m][f"top{n}"] for n in TOPS]
                if any(type(x) is not bool for x in flags) or (flags[0] and not flags[1]) or (flags[1] and not flags[2]):
                    raise ValueError("bad_topn_flags")
        except (KeyError, TypeError, ValueError):
            rejected["invalid_topn_flags"] += 1
            continue
        group["comparable"] += 1
        for m in MODES:
            for n in TOPS:
                group["topn_hits"][m][f"top{n}"] += int(comparison["modes"][m][f"top{n}"])
    groups = {}
    for (version, day), values in sorted(counts.items()):
        groups.setdefault(version, {})[day] = values
    return {"status": "historical_inventory_only", "formal": False,
            "independent_predeadline_proof": False, "groups": groups,
            "rejections": dict(rejected),
            "warning": "Exhaustive archived files; V1/V2 never pooled. No independent cutoff evidence or improvement claim."}


if __name__ == "__main__":
    print("ALL_VERSION_ARCHIVE_INVENTORY=" + json.dumps(inventory(), ensure_ascii=False, sort_keys=True))
