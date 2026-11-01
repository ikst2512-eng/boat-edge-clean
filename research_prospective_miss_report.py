"""Research-only miss diagnostics from existing audited prospective evaluations.

Local git first-add is NOT proof of remote receipt; never report formal hit rate.
"""
import argparse
import json
from pathlib import Path
from evaluate_clean_prospective import evaluate
from scripts.research_topn_miss_diagnostic import summarize_misses

ROOT = Path(__file__).resolve().parent


def report(day, root=ROOT, scorer=evaluate):
    if not isinstance(day, str) or len(day) != 8 or not day.isascii() or not day.isdigit() or not day.startswith("20"):
        raise ValueError("invalid day")
    root = Path(root)
    paths = sorted((root / "prospective_predictions").glob(day + "????.json"))
    rows = []
    counts = {"archives": len(paths), "evaluated": 0, "awaiting_result": 0, "audit_rejected": 0}
    rejected = []
    for path in paths:
        try:
            if path.is_symlink() or not path.is_file() or path.stat().st_size > 20000:
                raise ValueError("invalid archive")
            outcome = scorer(path.stem, root)
            if outcome.get("status") == "result_unavailable":
                counts["awaiting_result"] += 1
                continue
            if (outcome.get("status") != "evaluated" or outcome.get("audited") is not True
                    or outcome.get("formal") is not False
                    or outcome.get("scoring_kind") != "prospective_research_only"
                    or outcome.get("race_code") != path.stem
                    or not isinstance(outcome.get("first_add_sha"), str)):
                raise ValueError("untrusted evaluation")
            candidate = json.loads(path.read_text(encoding="utf-8"))
            result_path = root / "confirmed_results" / path.name
            if result_path.is_symlink() or not result_path.is_file() or result_path.stat().st_size > 20000:
                raise ValueError("missing immutable confirmed record")
            result = json.loads(result_path.read_text(encoding="utf-8"))
            finish = result.get("finish_order")
            if (candidate.get("race_code") != path.stem or result.get("race_code") != path.stem
                    or result.get("status") != "confirmed"
                    or not isinstance(finish, list) or len(finish) != 3):
                raise ValueError("untrusted result")
            winning = "-".join(map(str, finish))
            tickets = candidate.get("predictions")
            if outcome.get("winning_ticket") != winning:
                raise ValueError("result disagreement")
            # Validate each row before appending it to the shared cohort.
            row_summary = summarize_misses([(tickets, finish)])
            rank = tickets.index(winning) + 1 if winning in tickets else None
            if (outcome.get("rank") != rank or
                    any(outcome.get("top" + str(n)) is not (rank is not None and rank <= n)
                        for n in (3, 5, 10)) or
                    any(row_summary["top" + str(n)]["hits"] != int(rank is not None and rank <= n)
                        for n in (3, 5, 10))):
                raise ValueError("inconsistent frozen forecast rank")
            rows.append((tickets, finish))
            counts["evaluated"] += 1
        except (ValueError, KeyError, TypeError, OSError, AttributeError, IndexError) as exc:
            counts["audit_rejected"] += 1
            rejected.append({"race_code": path.stem, "reason": str(exc)[:100]})
    if counts["archives"] != sum(counts[k] for k in ("evaluated", "awaiting_result", "audit_rejected")):
        raise ValueError("incomplete cohort accounting")
    return {"schema": "CLEAN_PROSPECTIVE_MISS_DIAGNOSTIC_V1",
            "day_jst": day, "formal": False, "simulated_only": True,
            "remote_first_seen_verified": False, "counts": counts,
            "topn": summarize_misses(rows), "rejected": rejected,
            "warning": "Local git first-add evidence is not independently proven remote first-seen."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("day")
    args = parser.parse_args()
    print(json.dumps(report(args.day), ensure_ascii=False, sort_keys=True))
