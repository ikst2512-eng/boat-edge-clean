"""Re-audit source receipts from inventory-listed GitHub Actions archives, read-only."""
import argparse
import json
import os
from collections import Counter
from pathlib import Path
from zipfile import BadZipFile, LargeZipFile
from scripts.inspect_joint_t12_archive import load_archive
from scripts.reaudit_joint_t12_archive import reaudit_archive


def reaudit_inventory(inventory, repo, token, loader=load_archive, auditor=reaudit_archive):
    if inventory.get("repo") != repo or inventory.get("pagination_may_be_truncated") is not False:
        raise ValueError("incomplete or mismatched inventory")
    runs = inventory.get("runs")
    if not isinstance(runs, list) or inventory.get("real_dispatch_runs_seen") != len(runs):
        raise ValueError("invalid run inventory")
    if not token:
        raise ValueError("missing token")
    seen = set()
    seen_artifacts = set()
    results = []
    for run in runs:
        run_id = run.get("run_id")
        ids = run.get("matching_unexpired_artifact_ids")
        if type(run_id) is not int or run_id <= 0 or run_id in seen or not isinstance(ids, list):
            raise ValueError("invalid or duplicate run")
        if len(ids) > 1:
            raise ValueError("ambiguous multiple evidence artifacts for one run")
        seen.add(run_id)
        for artifact_id in ids:
            if type(artifact_id) is not int or artifact_id <= 0 or artifact_id in seen_artifacts:
                raise ValueError("invalid or duplicate artifact")
            seen_artifacts.add(artifact_id)
            try:
                result = auditor(loader(repo, token, artifact_id), run_id)
                verified = result["independently_verified_complete_pairs"]
                reports = result["attempt_reports"]
                if (type(verified) is not int or type(reports) is not int
                        or not 0 <= verified <= reports <= 6):
                    raise ValueError("invalid audit totals")
                results.append({"run_id": run_id, "artifact_id": artifact_id,
                                "verified_complete_pairs": verified,
                                "attempt_reports": result["attempt_reports"],
                                "status": "source_reaudit_complete"})
            except (ValueError, OSError, KeyError, TypeError, UnicodeError, EOFError,
                    BadZipFile, LargeZipFile, json.JSONDecodeError):
                results.append({"run_id": run_id, "artifact_id": artifact_id,
                                "verified_complete_pairs": 0,
                                "attempt_reports": None, "status": "source_reaudit_unresolved"})
    counts = Counter(r["status"] for r in results)
    return {"scope": "available artifacts only; source receipts independently audited",
            "artifact_results": results, "status_counts": dict(counts),
            "verified_complete_pair_attempts_in_inspected_artifacts": sum(
                r["verified_complete_pairs"] for r in results),
            "historical_success_rate": None,
            "full_history_verified": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    data = json.loads(Path(args.inventory).read_text(encoding="utf-8"))
    result = reaudit_inventory(data, args.repo, os.environ.get("GITHUB_TOKEN"))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "artifact_results"}, ensure_ascii=False))
