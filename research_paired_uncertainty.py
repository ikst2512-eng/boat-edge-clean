"""Statistical uncertainty for research-only paired trifecta rankings.

Does not train, modify, or promote any prediction model. Inference assumes
independently selected evaluation races; day-cluster bootstrap addresses some
within-day dependence. Inspect source provenance before reporting a real gain.
"""
import json
import math
import random
from collections import defaultdict
from pathlib import Path

from research_paired_evaluation import TOP_K, rankings, validate


def exact_mcnemar_p(candidate_only, baseline_only):
    """Two-sided exact McNemar / binomial discordance test."""
    n = candidate_only + baseline_only
    if n == 0:
        return 1.0
    small = min(candidate_only, baseline_only)
    # Binomial tail calculated by stable recurrence (no scipy dependency).
    term = 2.0 ** (-n)
    cumulative = term
    for i in range(1, small + 1):
        term *= (n - i + 1) / i
        cumulative += term
    return min(1.0, 2 * cumulative)


def summarize(rows, *, resamples=4000, seed=20261027):
    if not rows:
        raise ValueError("at least one paired race required")
    if type(resamples) is not int or resamples < 100:
        raise ValueError("at least 100 bootstrap replicates required")
    days = defaultdict(list)
    seen = set()
    for source in rows:
        row = validate(source)
        code = row["race_code"]
        if code in seen:
            raise ValueError("duplicate race_code")
        seen.add(code)
        base = rankings(row["baseline"])
        candidate = rankings(row["candidate"])
        days[code[:8]].append({
            k: (int(row["actual"] in candidate[:k]) -
                int(row["actual"] in base[:k])) for k in TOP_K
        })
    all_deltas = [point for day in days.values() for point in day]
    n = len(all_deltas)
    rng = random.Random(seed)
    date_keys = sorted(days)
    report = {"races": n, "days": len(date_keys), "bootstrap_unit": "race_date",
              "resamples": resamples, "top_k": {}}
    for k in TOP_K:
        gains = sum(p[k] == 1 for p in all_deltas)
        losses = sum(p[k] == -1 for p in all_deltas)
        differences = []
        for _ in range(resamples):
            picked = [rng.choice(date_keys) for _ in date_keys]
            values = [p[k] for d in picked for p in days[d]]
            differences.append(sum(values) / len(values))
        differences.sort()
        lo = differences[int(0.025 * resamples)]
        hi = differences[min(resamples - 1, math.ceil(0.975 * resamples) - 1)]
        report["top_k"][str(k)] = {
            "candidate_only_hits": gains, "baseline_only_hits": losses,
            "paired_delta": (gains - losses) / n,
            "cluster_bootstrap_95pct_ci": [lo, hi],
            "mcnemar_exact_p_unadjusted": exact_mcnemar_p(gains, losses)
        }
    report["warning"] = (
        "Exploratory only: do not treat CI or unadjusted p-values as proof "
        "when models/hyperparameters were selected on these races. "
        "Require timestamp provenance, chronological untouched holdout, "
        "minimum sample-size and multiple-testing policy."
    )
    return report


def evaluate(path):
    rows = []
    with Path(path).open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return summarize(rows)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("frozen_jsonl")
    parser.add_argument("--resamples", type=int, default=4000)
    args = parser.parse_args()
    print(json.dumps(evaluate(args.frozen_jsonl), ensure_ascii=False, indent=2))
