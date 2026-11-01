"""Read-only AI operations gate. Does not retrain, deploy, or modify forecasts."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from research_chronological_calibration import load_pairs, report

DEFAULT_OUTPUT = Path("ai_operations_report.json")


def assess(calibration):
    status = calibration.get("status")
    if status != "research_backtest_only":
        return {
            "decision": "insufficient_evidence",
            "production_change_allowed": False,
            "reason": status or "unknown_evidence_status",
            "next_action": "Collect verified, pre-cutoff prospective predictions and independent outcomes.",
        }
    baseline = calibration["holdout_baseline_beta_0_4"]
    candidate = calibration["holdout_selected"]
    top_n = (3, 5, 10)
    regressions = [k for k in top_n if candidate[f"top{k}"] < baseline[f"top{k}"]]
    return {
        "decision": "research_candidate_only" if not regressions else "research_candidate_regressed",
        "production_change_allowed": False,
        "reason": "Holdout research is exploratory and lacks audited first-Git-add evidence."
        if not regressions else "Holdout regression in Top" + ",".join(map(str, regressions)),
        "baseline": baseline,
        "candidate": candidate,
        "next_action": "Run independently timestamp-audited prospective evaluation before any promotion.",
    }


def build_report(rows=None):
    if rows is None:
        rows = load_pairs()
    calibration = report(rows)
    return {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "offline_read_only_research",
        "calibration": calibration,
        "gate": assess(calibration),
        "automatic_model_promotion": False,
        "automatic_production_code_change": False,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    payload = build_report()
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"decision": payload["gate"]["decision"], "output": str(args.output)}))


if __name__ == "__main__":
    main()
