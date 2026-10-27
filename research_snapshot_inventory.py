"""Read-only inventory of frozen research forecasts; never opens outcomes or formal Fresh."""
import argparse
import json
from collections import Counter
from pathlib import Path
from datetime import datetime, timedelta

REQUIRED = ("race_code", "predictions", "generated_at", "cutoff_jst",
            "source_deadline_jst", "model_git_sha", "input_sha256",
            "source_title_sha256", "source_cards_sha256")

def inventory(root):
    counts = Counter()
    reasons = Counter()
    models = Counter()
    for path in sorted(Path(root).glob("*.json")):
        counts["files"] += 1
        try:
            if path.is_symlink() or path.stat().st_size > 20000:
                raise ValueError("unsafe_file")
            o = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(o, dict) or o.get("race_code") != path.stem:
                raise ValueError("identity_mismatch")
            if o.get("status") != "research" or o.get("validated") is not False:
                raise ValueError("not_research")
            picks = o.get("predictions")
            if not isinstance(picks, list) or len(picks) != 10 or len(set(picks)) != 10:
                raise ValueError("invalid_top10")
            counts["structurally_valid_top10"] += 1
            models[str(o.get("model_version", "unknown"))] += 1
            missing = [key for key in REQUIRED if not o.get(key)]
            if missing:
                reasons["missing_provenance_fields"] += 1
                continue
            generated = datetime.fromisoformat(o["generated_at"])
            deadline = datetime.fromisoformat(o["source_deadline_jst"])
            cutoff = datetime.fromisoformat(o["cutoff_jst"])
            if any(d.tzinfo is None or d.utcoffset() is None for d in (generated, deadline, cutoff)):
                raise ValueError("naive_timestamps")
            if cutoff != deadline-timedelta(minutes=12) or generated > cutoff:
                raise ValueError("cutoff_violation")
            counts["local_metadata_complete"] += 1
            # Snapshot metadata never establishes independent first-add / remote receipt.
            reasons["independent_git_receipt_and_result_required"] += 1
        except (ValueError, TypeError, KeyError, AttributeError, json.JSONDecodeError) as exc:
            reasons[str(exc)] += 1
    return {
        "status": "INVENTORY_ONLY_NOT_RESULT_SCORING",
        "counts": dict(counts), "models": dict(models), "reasons": dict(reasons),
        "formally_scoreable_from_snapshot_alone": 0,
        "note": "Original Git first addition, trusted remote timestamp, independent source authenticity and final official result are not inferred."
    }

if __name__ == "__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--snapshots", default="research_snapshots")
    a=p.parse_args()
    print(json.dumps(inventory(a.snapshots), ensure_ascii=False, indent=2))
