"""Read-only audit of saved research Top10 against deterministic baseline replay.

A replay match establishes reproducibility, NOT independent pre-cutoff proof.
Never writes snapshots or calls live sources; never scores an actual outcome.
"""
import argparse
import json
from collections import Counter
from pathlib import Path

from research_model import probabilities

def audit_snapshot(record):
    if not isinstance(record, dict):
        raise ValueError("record not object")
    code = record.get("race_code")
    if not isinstance(code, str) or len(code) != 12 or not code.isascii() or not code.isdigit():
        raise ValueError("invalid race_code")
    if record.get("status") != "research" or record.get("validated") is not False:
        raise ValueError("not unvalidated research")
    saved = record.get("predictions")
    if not isinstance(saved, list) or len(saved) != 10 or len(set(saved)) != 10:
        raise ValueError("Top10 invalid")
    expected = ["-".join(map(str, t)) for t, _ in probabilities(record["national_win_rates"])[:10]]
    # This audit only knows the exact legacy model; do not apply to other versions.
    version = record.get("model_version")
    if version != "national-beta0.4-exploratory-v1":
        return {"race_code": code, "version_supported": False, "replay_matches": None,
                "prospective_verified": False}
    return {"race_code": code, "version_supported": True,
            "replay_matches": saved == expected,
            "prospective_verified": False}

def audit_directory(directory):
    root = Path(directory)
    if not root.is_dir():
        raise ValueError("directory missing")
    results = []
    keys = set()
    for path in sorted(root.glob("*.json")):
        try:
            item = audit_snapshot(json.loads(path.read_text(encoding="utf-8")))
            if path.stem != item["race_code"]:
                raise ValueError("filename race mismatch")
            if path.stem in keys:
                raise ValueError("duplicate race")
            keys.add(path.stem)
            item["file"] = path.name
        except (ValueError, TypeError, KeyError, OSError) as exc:
            item = {"file": path.name, "error": str(exc), "prospective_verified": False}
        results.append(item)
    return {"files": len(results), "supported": sum(x.get("version_supported") is True for x in results),
            "replay_matches": sum(x.get("replay_matches") is True for x in results),
            "replay_mismatches": sum(x.get("replay_matches") is False for x in results),
            "invalid": sum("error" in x for x in results),
            "unsupported": sum(x.get("version_supported") is False for x in results),
            "prospective_verified": 0,
            "warning": "Replay matching is not independently verified pre-cutoff evidence.",
            "details": results}

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("directory")
    args = p.parse_args()
    print(json.dumps(audit_directory(args.directory), ensure_ascii=False, indent=2))
