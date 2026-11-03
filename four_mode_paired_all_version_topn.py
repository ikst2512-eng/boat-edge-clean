"""Read-only same-race paired TopN comparison, separated by model version/date."""
import json
import re
from collections import defaultdict
from pathlib import Path
from four_mode_frozen_diagnostic import compare_race

ROOT = Path(__file__).resolve().parent
TOPS = (3, 5, 10)
PAIRS = (("hit", "balance"), ("narrow", "hit"), ("balance", "hole"))


def paired_audit(root=ROOT):
    root = Path(root)
    grouped = defaultdict(list)
    excluded = defaultdict(int)
    for path in sorted((root / "four_mode_forecasts").glob("*.json")):
        code = path.stem
        if not re.fullmatch(r"20[0-9]{10}", code):
            continue
        if path.is_symlink() or path.stat().st_size > 30000:
            excluded["unsafe_forecast"] += 1
            continue
        try:
            forecast = json.loads(path.read_text(encoding="utf-8"))
            version = forecast["model_version"]
            if forecast.get("race_code") != code or not re.fullmatch(r"CLEAN_FOUR_MODES_V[0-9]+_[A-Z0-9_]+", version):
                raise ValueError("invalid_version")
            record = compare_race(code, root)
            if record.get("status") != "historical_comparison_only":
                excluded[record.get("status", "unavailable")] += 1
                continue
            for left, right in PAIRS:
                for mode in (left, right):
                    flags = [record["modes"][mode][f"top{n}"] for n in TOPS]
                    if any(type(x) is not bool for x in flags) or not (flags[0] <= flags[1] <= flags[2]):
                        raise ValueError("invalid_flags")
        except (OSError, ValueError, KeyError, TypeError):
            excluded["invalid_record"] += 1
            continue
        grouped[(version, code[:8])].append(record)
    groups = {}
    for (version, day), records in sorted(grouped.items()):
        pairs = {}
        for left, right in PAIRS:
            per_top = {}
            for n in TOPS:
                flag = f"top{n}"
                both = sum(r["modes"][left][flag] and r["modes"][right][flag] for r in records)
                left_only = sum(r["modes"][left][flag] and not r["modes"][right][flag] for r in records)
                right_only = sum(not r["modes"][left][flag] and r["modes"][right][flag] for r in records)
                neither = len(records) - both - left_only - right_only
                per_top[flag] = {"both": both, "left_only": left_only,
                                 "right_only": right_only, "neither": neither,
                                 "net_right_minus_left": right_only - left_only}
            pairs[f"{left}_vs_{right}"] = per_top
        groups.setdefault(version, {})[day] = {"evaluated": len(records), "paired": pairs}
    return {"status": "historical_paired_only", "formal": False,
            "independent_predeadline_proof": False, "groups": groups,
            "excluded": dict(excluded), "warning": "No causal improvement, no independent holdout, no production promotion."}


if __name__ == "__main__":
    print("PAIRED_ALL_VERSION_TOPN=" + json.dumps(paired_audit(), sort_keys=True))
