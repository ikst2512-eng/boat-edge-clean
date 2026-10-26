"""Read-only audit of research snapshot input provenance. No scoring/unlock."""
import hashlib
import re
from datetime import datetime, timedelta, timezone

JST = timezone(timedelta(hours=9))
HEX = re.compile(r"^[0-9a-f]{64}$")


def audit_snapshot(record):
    if not isinstance(record, dict) or not re.fullmatch(r"20[0-9]{10}", str(record.get("race_code", ""))):
        return {"status": "blocked_identity", "verified": False}
    try:
        generated = datetime.fromisoformat(record["generated_at"])
        cutoff = datetime.fromisoformat(record["cutoff_jst"])
        received = [datetime.fromisoformat(record[k]) for k in
                    ("source_title_received_jst", "source_cards_received_jst")]
        if any(x.utcoffset() is None for x in [generated, cutoff, *received]):
            raise ValueError("naive clock")
        source_deadline = datetime.fromisoformat(record["source_deadline_jst"])
        if source_deadline.utcoffset() is None:
            raise ValueError("naive deadline")
        if cutoff != source_deadline - timedelta(minutes=12):
            return {"status": "blocked_cutoff_mismatch", "verified": False}
        if max(received) > generated or generated > cutoff:
            return {"status": "blocked_temporal_order", "verified": False}
    except (KeyError, ValueError, TypeError):
        return {"status": "blocked_time_evidence_incomplete", "verified": False}
    hashes = [record.get(k) for k in ("source_title_sha256", "source_cards_sha256")]
    aggregate = record.get("input_sha256")
    if not all(isinstance(x, str) and HEX.fullmatch(x) for x in [*hashes, aggregate]):
        return {"status": "blocked_missing_source_hash", "verified": False}
    calculated = hashlib.sha256((hashes[0] + ":" + hashes[1]).encode("ascii")).hexdigest()
    if aggregate != calculated or record.get("input_hash_scope") != "source_csv_byte_hashes_ordered_title_cards":
        return {"status": "blocked_input_hash_mismatch", "verified": False}
    return {"status": "metadata_self_consistent_unverified", "verified": False,
            "source_bytes_independently_verified": False,
            "official_preview_bound": False,
            "prediction_snapshot_proven": False}

def audit_saved_directory(directory):
    """Summarize evidence coverage only; never edit saved research predictions."""
    import json
    from collections import Counter
    from pathlib import Path
    counts = Counter()
    total = 0
    for file in sorted(Path(directory).glob("*.json")):
        total += 1
        try:
            with file.open(encoding="utf-8") as stream:
                record = json.load(stream)
            status = audit_snapshot(record)["status"]
        except (OSError, ValueError, TypeError):
            status = "blocked_unreadable_json"
        counts[status] += 1
    return {"total": total, "statuses": dict(sorted(counts.items())),
            "all_verified": False, "snapshot_source_bytes_authenticated": False}


if __name__ == "__main__":
    import argparse
    import json
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", default="research_snapshots")
    args = parser.parse_args()
    print(json.dumps(audit_saved_directory(args.directory), sort_keys=True))
