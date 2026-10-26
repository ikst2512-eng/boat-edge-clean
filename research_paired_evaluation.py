"""Research-only paired trifecta evaluation. Never reads or writes formal Fresh files.

Input: JSONL, one frozen pre-race comparison per race:
{"race_code":"202610271201","generated_at":"2026-10-27T10:00:00+09:00",
 "cutoff_jst":"2026-10-27T10:12:00+09:00","actual":"1-2-3",
 "baseline":{"1-2-3":0.01,...120 tickets...},
 "candidate":{"1-2-3":0.02,...120 tickets...}}
Require independently proven timestamps / immutable snapshots before interpreting results.
"""
import argparse
import json
import math
from datetime import datetime
from itertools import permutations
from pathlib import Path

TICKETS = {"-".join(map(str, p)) for p in permutations(range(1, 7), 3)}
TOP_K = (1, 3, 5, 10)


def validate(row):
    if not isinstance(row, dict):
        raise ValueError("expected object")
    code = row.get("race_code")
    if not isinstance(code, str) or len(code) != 12 or not code.isascii() or not code.isdigit():
        raise ValueError("invalid race_code")
    issued = datetime.fromisoformat(row["generated_at"])
    cutoff = datetime.fromisoformat(row["cutoff_jst"])
    if issued.tzinfo is None or cutoff.tzinfo is None or issued >= cutoff:
        raise ValueError("missing or post-cutoff prediction")
    actual = row.get("actual")
    if actual not in TICKETS:
        raise ValueError("unscorable or invalid finish")
    for name in ("baseline", "candidate"):
        probabilities = row.get(name)
        if not isinstance(probabilities, dict) or set(probabilities) != TICKETS:
            raise ValueError(f"{name} must have 120 exact tickets")
        if any(type(p) not in (float, int) or not math.isfinite(p) or p < 0 or p > 1
               for p in probabilities.values()):
            raise ValueError(f"{name} contains invalid probability")
        if not math.isclose(sum(probabilities.values()), 1.0, abs_tol=1e-8, rel_tol=0):
            raise ValueError(f"{name} probabilities not normalized")
    return row


def rankings(probs):
    return sorted(TICKETS, key=lambda t: (-probs[t], t))


def metrics(rows):
    n = len(rows)
    if not n:
        raise ValueError("no valid races")
    output = {"races": n}
    for model in ("baseline", "candidate"):
        hits = {k: 0 for k in TOP_K}
        loss = 0.0
        for row in rows:
            ranking = rankings(row[model])
            for k in TOP_K:
                hits[k] += row["actual"] in ranking[:k]
            loss -= math.log(max(row[model][row["actual"]], 1e-15))
        output[model] = {"top_hits": {str(k): hits[k] for k in TOP_K},
                         "top_rates": {str(k): hits[k] / n for k in TOP_K},
                         "log_loss": loss / n}
    output["paired_deltas"] = {
        str(k): output["candidate"]["top_rates"][str(k)] -
                output["baseline"]["top_rates"][str(k)] for k in TOP_K
    }
    return output


def evaluate(path):
    rows = []
    seen = set()
    with Path(path).open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                row = validate(json.loads(line))
            except (ValueError, KeyError, TypeError) as exc:
                raise ValueError(f"line {line_no}: {exc}") from exc
            if row["race_code"] in seen:
                raise ValueError(f"line {line_no}: duplicate race")
            seen.add(row["race_code"])
            rows.append(row)
    return metrics(rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Research-only paired offline evaluation")
    parser.add_argument("frozen_jsonl", help="Full 120-probability baseline/candidate snapshots + actual")
    args = parser.parse_args()
    print(json.dumps(evaluate(args.frozen_jsonl), indent=2, ensure_ascii=False))
