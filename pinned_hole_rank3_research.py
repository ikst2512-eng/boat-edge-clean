"""Reproduce an already-proposed hole 2nd-pair swap on exact 240 frozen race IDs.

Counterfactual retrospective *research*, not prospectively validated betting advice.
Selection uses frozen tickets only; confirmed results are loaded strictly afterward.
"""
import json
import math
import re
from pathlib import Path

from four_mode_archive_api import archived_four_modes
from four_mode_frozen_diagnostic import compare_race
from four_mode_historical_cohort import ROOT
from hole_upper_rank_pair_protection import propose
from pinned_four_mode_cohort_audit import load_locked_manifest, MANIFEST

TOPS = (1, 3, 5, 10)


def _tickets(archive, mode):
    raw = archive["modes"][mode]["tickets"]
    tickets = [row["combo"] for row in raw]
    if (not tickets or len(tickets) != len(set(tickets))
            or any(type(t) is not str or re.fullmatch(r"[1-6]-[1-6]-[1-6]", t) is None
                   or len(set(t.split("-"))) != 3 for t in tickets)):
        raise ValueError("untrusted_original_tickets")
    return tickets


def score_one(code, root=ROOT, archive_loader=archived_four_modes,
              selector=propose, result_loader=compare_race):
    # A race result MUST NOT influence candidate selection. Preserve this order.
    status, archive = archive_loader(code, root)
    if status != 200:
        return {"race_code": code, "status": "archive_unavailable"}
    baseline = _tickets(archive, "hole")[:10]
    donor = _tickets(archive, "hit")
    if len(baseline) != 10:
        raise ValueError("insufficient_original_top10")
    candidate = selector(baseline, donor, 3)
    if (type(candidate) is not list or len(candidate) != 10
            or len(set(candidate)) != 10
            or baseline[:2] != candidate[:2]
            or not {tuple(t.split("-")[:2]) for t in baseline}.issubset(
                {tuple(t.split("-")[:2]) for t in candidate})):
        raise ValueError("selector_changed_budget_or_pair_coverage")
    added = [x for x in candidate if x not in baseline]
    removed = [x for x in baseline if x not in candidate]
    if len(added) != len(removed):
        raise ValueError("selector_change_unbalanced")
    # Only after the selection is frozen can confirmed finishes be inspected.
    result = result_loader(code, root)
    if (result.get("status") != "historical_comparison_only"
            or result.get("formal") is not False
            or result.get("remote_first_seen_verified") is not False):
        return {"race_code": code, "status": "result_unavailable_or_untrusted"}
    winner = result.get("winning_ticket")
    if (type(winner) is not str
            or re.fullmatch(r"[1-6]-[1-6]-[1-6]", winner) is None
            or len(set(winner.split("-"))) != 3):
        raise ValueError("untrusted_result_ticket")
    by_top = {}
    for n in TOPS:
        before, after = winner in baseline[:n], winner in candidate[:n]
        by_top[f"top{n}"] = {
            "baseline": before, "candidate": after,
            "gained": after and not before, "lost": before and not after,
        }
    return {"race_code": code, "status": "historical_comparison_only",
            "formal": False, "winning_ticket": winner,
            "changed": baseline != candidate,
            "added": added, "removed": removed, "topn": by_top}


def paired_exact_two_sided_p(gained, lost):
    """Two-sided exact McNemar/binomial p, conditional on discordant races.

    Descriptive only. No multiple-scenario or model-selection correction.
    """
    n = gained + lost
    if n == 0:
        return None
    tail = sum(math.comb(n, k) for k in range(min(gained, lost) + 1))
    return min(1.0, 2.0 * tail / (2 ** n))


def run(root=ROOT, manifest_path=MANIFEST, scorer=score_one):
    manifest, digest = load_locked_manifest(manifest_path)
    info = manifest["cohorts"]["holdout_240"]
    codes = info["codes"]
    rows = [scorer(code, root) for code in codes]
    valid = [r for r in rows if r.get("status") == "historical_comparison_only"]
    if len(valid) != len({r["race_code"] for r in valid}):
        raise ValueError("duplicate_scored_race")
    complete = len(valid) == len(codes)
    stats = {}
    for n in TOPS:
        key = f"top{n}"
        before = sum(r["topn"][key]["baseline"] for r in valid)
        after = sum(r["topn"][key]["candidate"] for r in valid)
        gained = sum(r["topn"][key]["gained"] for r in valid)
        lost = sum(r["topn"][key]["lost"] for r in valid)
        if after - before != gained - lost:
            raise ValueError("paired_gain_loss_reconciliation")
        stats[key] = {
            "baseline_hits_on_valid_only": before,
            "candidate_hits_on_valid_only": after,
            "gained": gained, "lost": lost, "net": gained - lost,
            "baseline_pct": round(100 * before / len(codes), 2) if complete else None,
            "candidate_pct": round(100 * after / len(codes), 2) if complete else None,
            "exact_p_uncorrected_exploratory": (
                round(paired_exact_two_sided_p(gained, lost), 6) if complete
                and gained + lost else None),
        }
    return {
        "schema": "HOLE_PINNED_HISTORICAL_RANK3_REPLAY_V1",
        "status": "historical_complete" if complete else "incomplete_historical_evidence",
        "formal": False, "prospective_validation": False,
        "remote_first_seen_verified": False, "model_improvement_proven": False,
        "production_forecast_changed": False,
        "selection": "existing_predeclared_hit_rank3_pair_protected",
        "source_actions_run_id": info["actions_run_id"],
        "source_artifact_id": info["artifact_id"],
        "roster_sha256": info["sha256"], "manifest_sha256": digest,
        "requested": len(codes), "comparable": len(valid),
        "changed": sum(r["changed"] for r in valid),
        "unavailable": [r for r in rows if r.get("status") != "historical_comparison_only"],
        "topn": stats if complete else None,
        "partial_count_diagnostics": stats if not complete else None,
        "per_race": valid,
        "warning": ("Retrospective race-ID-disjoint, but same-calendar-period research; "
                    "not an independent temporal prospective holdout. Exact p-values "
                    "are descriptive and uncorrected for choosing among tested policies.")
    }


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--output", default="pinned_hole_rank3_research_report.json")
    args = p.parse_args()
    report = run()
    Path(args.output).write_text(json.dumps(report, ensure_ascii=False, sort_keys=True,
                                            indent=2) + "\n", encoding="utf-8")
    print("PINNED_HOLE_RANK3=" + json.dumps({
        key: report[key] for key in
        ("status", "formal", "requested", "comparable", "changed", "topn")
    }, ensure_ascii=False, sort_keys=True))
    return 0 if report["status"] == "historical_complete" else 2


if __name__ == "__main__":
    raise SystemExit(main())
