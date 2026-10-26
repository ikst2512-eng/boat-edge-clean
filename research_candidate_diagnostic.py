"""Research-only candidate diagnostic with no invented outcomes or hit-rate claims.

Reads JSONL records with six national win rates and *pre-cutoff confirmed*
course entries. Never contacts live services or writes forecasts.
Records lacking verified entry are evaluated with default-entry assumption
only when explicitly requested and always flagged; never counted as verified.
"""
import argparse
import json
from collections import Counter
from pathlib import Path
from research_model import probabilities
from research_scenario_candidate import scenario_probabilities

FEATURES = ("motor", "exhibition", "st", "fl")

def _tickets(items):
    return {"-".join(map(str, ticket)): p for ticket, p in items}

def inspect(row):
    if not isinstance(row, dict):
        raise ValueError("record must be an object")
    code = row.get("race_code")
    if not isinstance(code, str) or len(code) != 12 or not code.isascii() or not code.isdigit():
        raise ValueError("invalid race code")
    rates = row["national_win_rates"]
    entry = row.get("entry")
    entry_status = row.get("entry_status", "missing")
    if entry_status not in ("pre_cutoff_verified", "missing", "unverified"):
        raise ValueError("unrecognized entry_status")
    if entry_status == "pre_cutoff_verified" and entry is None:
        raise ValueError("verified entry requires entry")
    if entry is None:
        entry = (1, 2, 3, 4, 5, 6)
    baseline = _tickets(probabilities(rates))
    options = {key: row.get(key) for key in FEATURES}
    candidate = _tickets(scenario_probabilities(rates, entry, **options))
    baseline_top = sorted(baseline, key=lambda t: (-baseline[t], t))
    candidate_top = sorted(candidate, key=lambda t: (-candidate[t], t))
    missing = []
    for key in FEATURES:
        values = options[key]
        if values is None:
            missing.append(key)
        elif any(v is None for v in values):
            missing.append(key + "_partial")
    return {"race_code": code, "entry_status": entry_status,
            "entry_assumed": entry_status != "pre_cutoff_verified",
            "missing_features": missing,
            "baseline_top10": baseline_top[:10],
            "candidate_top10": candidate_top[:10],
            "top1_changed": baseline_top[0] != candidate_top[0],
            "top10_overlap": len(set(baseline_top[:10]) & set(candidate_top[:10])),
            "actual_scored": False}

def diagnostic(path):
    output = []
    seen = set()
    for line_no, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            item = inspect(json.loads(line))
        except (ValueError, TypeError, KeyError) as exc:
            raise ValueError(f"line {line_no}: {exc}") from exc
        if item["race_code"] in seen:
            raise ValueError(f"line {line_no}: duplicate race")
        seen.add(item["race_code"])
        output.append(item)
    return {"races": len(output), "verified_entry": sum(not r["entry_assumed"] for r in output),
            "entry_assumed": sum(r["entry_assumed"] for r in output),
            "top1_changes": sum(r["top1_changed"] for r in output),
            "missing_feature_counts": dict(Counter(x for row in output for x in row["missing_features"])),
            "diagnostics": output,
            "note": "Diagnostic ranking differences only; cannot establish hit-rate gain."}

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("input_jsonl")
    args = p.parse_args()
    print(json.dumps(diagnostic(args.input_jsonl), ensure_ascii=False, indent=2))
