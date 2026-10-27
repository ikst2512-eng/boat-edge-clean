"""Read-only preflight for saved research snapshots; never fetches outcomes."""
import argparse
import json
from itertools import permutations
from pathlib import Path

TICKETS = {"-".join(map(str, t)) for t in permutations(range(1, 7), 3)}

def inspect(record):
    if not isinstance(record, dict) or record.get("status") != "research":
        return {"ready": False, "reason": "invalid research envelope"}
    predictions = record.get("predictions")
    if not isinstance(predictions, list) or len(predictions) != 10 or len(set(predictions)) != 10 or any(x not in TICKETS for x in predictions):
        return {"ready": False, "reason": "invalid top10 snapshot"}
    full = record.get("probabilities")
    if not isinstance(full, dict) or set(full) != TICKETS:
        return {"ready": False, "reason": "top10 only; 120-way probabilities not frozen"}
    # Presence is not proof of an independent first-seen receipt or data provenance.
    return {"ready": False, "reason": "120-way values present; independent original-byte and pre-deadline receipts still require audit"}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("snapshot", type=Path)
    args = p.parse_args()
    result = inspect(json.loads(args.snapshot.read_text(encoding="utf-8")))
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
