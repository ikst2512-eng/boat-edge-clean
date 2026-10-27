"""Offline, paired chronological evaluation of CLEAN's 120-way research model.

Uses independently verified pre-deadline six win rates and allowed final results.
CSV/JSON integrity and timing checks are necessary, not proof of external authenticity.
No production files, old repos, or results API are read/written.
"""
import argparse
import json
import math
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from research_model import probabilities

def aware(value):
    d = datetime.fromisoformat(value)
    if d.tzinfo is None or d.utcoffset() is None:
        raise ValueError("timezone-aware timestamps required")
    return d

def eligible_rows(items):
    if not isinstance(items, list):
        raise ValueError("expected array")
    rows, seen = [], set()
    excluded = Counter()
    for row in items:
        try:
            if not isinstance(row, dict):
                raise ValueError("invalid row")
            key = row["race_code"]
            if not isinstance(key, str) or len(key) != 12 or not key.isascii() or not key.isdigit() or key in seen:
                raise ValueError("duplicate_or_invalid_race")
            seen.add(key)
            if row.get("independent_receipt_verified") is not True or row.get("result_verified") is not True:
                raise ValueError("unverified_receipt_or_result")
            for field in ("input_sha256", "first_git_blob_sha", "receipt_sha256"):
                value = row.get(field)
                if not isinstance(value, str) or len(value) not in (40, 64) or any(c not in "0123456789abcdef" for c in value):
                    raise ValueError("missing_immutable_digest")
            source, generated, frozen = (aware(row[k]) for k in ("source_received_at", "generated_at", "first_seen_at"))
            deadline = aware(row["deadline"])
            if not (source <= generated <= frozen <= deadline - timedelta(minutes=12)):
                raise ValueError("cutoff_violation")
            rates = row["national_win_rates"]
            if len(rates) != 6 or any(type(v) not in (float, int) or not math.isfinite(v) or v <= 0 or v >= 20 for v in rates):
                raise ValueError("invalid_win_rates")
            outcome = tuple(int(x) for x in row["result"].split("-"))
            if len(outcome) != 3 or len(set(outcome)) != 3 or any(x not in range(1, 7) for x in outcome):
                raise ValueError("invalid_result")
            rows.append((key, rates, outcome, deadline))
        except (ValueError, KeyError, TypeError, AttributeError) as exc:
            excluded[str(exc)] += 1
    return rows, excluded

def metrics(rows, beta):
    count = len(rows)
    hits = Counter()
    loss = 0.0
    for _, rates, outcome, _ in rows:
        ranking = probabilities(rates, beta=beta)
        order = [ticket for ticket, _ in ranking]
        for n in (1, 3, 5, 10):
            hits[n] += int(outcome in order[:n])
        p = dict(ranking)[outcome]
        loss -= math.log(p)
    return {"n": count, "beta": beta, "hits": {f"top{n}": hits[n] for n in (1,3,5,10)},
            "rates": {f"top{n}": hits[n]/count if count else None for n in (1,3,5,10)},
            "mean_log_loss": loss/count if count else None}

def evaluate(items, betas=(0.0, 0.2, 0.4, 0.6, 0.8), holdout_fraction=0.3):
    rows, exclusions = eligible_rows(items)
    rows.sort(key=lambda row: (row[3], row[0]))
    split = int(len(rows)*(1-holdout_fraction))
    train, holdout = rows[:split], rows[split:]
    if not train or not holdout:
        return {"status":"INSUFFICIENT_EVIDENCE", "eligible":len(rows), "excluded":dict(exclusions)}
    training = [metrics(train, b) for b in betas]
    # Select beta only on chronological training data; never tune on holdout.
    selected = sorted(training, key=lambda x:(-x["rates"]["top3"], x["mean_log_loss"], abs(x["beta"]-0.4)))[0]["beta"]
    baseline = metrics(holdout, 0.4)
    candidate = metrics(holdout, selected)
    status = "DESCRIPTIVE_ONLY" if len(holdout) < 30 else "NEEDS_INDEPENDENT_EVIDENCE_AUDIT"
    return {"status":status, "eligible":len(rows), "excluded":dict(exclusions),
            "train_n":len(train), "holdout_n":len(holdout),
            "selected_beta":selected, "baseline_holdout":baseline, "candidate_holdout":candidate,
            "top3_delta":candidate["rates"]["top3"]-baseline["rates"]["top3"],
            "warning":"Self-declared verified flags and hashes are not independent receipts. Never promote or deploy from this report alone."}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("approved_input_json")
    args = parser.parse_args()
    print(json.dumps(evaluate(json.loads(Path(args.approved_input_json).read_text(encoding="utf-8"))), indent=2))
