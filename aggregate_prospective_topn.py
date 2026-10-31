"""Aggregate audited prospective Top-N cohorts across dates without treating pending as misses."""
import argparse
import json
from evaluate_clean_prospective_cohort import cohort


def summary(days, evaluator=cohort):
    if not days or len(set(days)) != len(days):
        raise ValueError("unique days required")
    counts = {k: 0 for k in ("archives", "evaluated", "awaiting_result", "audit_rejected")}
    hits = {f"top{n}": 0 for n in (3, 5, 10)}
    roi = {k: {"races": 0, "invested_yen": 0, "return_yen": 0} for k in hits}
    rows = []
    rejection_reasons = {}
    rejection_reasons = {}
    for day in sorted(days):
        if not isinstance(day, str) or len(day) != 8 or not day.isascii() or not day.isdigit() or not day.startswith("20"):
            raise ValueError("invalid day")
        result = evaluator(day)
        if result.get("schema") != "CLEAN_PROSPECTIVE_TOPN_COHORT_V1" or result.get("day_jst") != day or result.get("formal") is not False or result.get("simulated_only") is not True or result.get("first_add_audit_required") is not True:
            raise ValueError("untrusted cohort")
        daily = result["counts"]
        for rejected in result.get("rejected", []):
            reason = rejected.get("reason", "unclassified")
            rejection_reasons[reason] = rejection_reasons.get(reason, 0) + 1
        if any(type(daily.get(k)) is not int or daily[k] < 0 for k in counts):
            raise ValueError("invalid cohort counts")
        if daily["archives"] != daily["evaluated"] + daily["awaiting_result"] + daily["audit_rejected"]:
            raise ValueError("incomplete cohort accounting")
        for k in counts:
            counts[k] += daily[k]
        for k in hits:
            v = result["hits"][k]
            if type(v) is not int or not 0 <= v <= daily["evaluated"]:
                raise ValueError("invalid cohort hits")
            hits[k] += v
            entry = result["roi"][k]
            if any(type(entry.get(field)) is not int or entry[field] < 0 for field in ("races", "invested_yen", "return_yen")) or entry["races"] > daily["evaluated"] or entry["invested_yen"] != entry["races"] * 5000:
                raise ValueError("invalid roi evidence")
            for field in roi[k]:
                roi[k][field] += entry[field]
        if not hits["top3"] <= hits["top5"] <= hits["top10"]:
            raise ValueError("inconsistent top-n totals")
        reasons = {}
        for item in result.get("rejected", []):
            label = item.get("reason") if isinstance(item, dict) else None
            if not isinstance(label, str) or not label:
                label = "unspecified"
            label = label.split(":", 1)[0][:100]
            reasons[label] = reasons.get(label, 0) + 1
        if sum(reasons.values()) != daily["audit_rejected"]:
            raise ValueError("inconsistent audit rejection accounting")
        for label, quantity in reasons.items():
            rejection_reasons[label] = rejection_reasons.get(label, 0) + quantity
        rows.append({"day_jst": day, "counts": daily, "hits": result["hits"], "rejection_reasons": reasons})
    return {
        "schema": "CLEAN_PROSPECTIVE_TOPN_MULTIDAY_V1",
        "formal": False, "simulated_only": True, "calibrated_confidence": False,
        "days": rows, "counts": counts, "hits": hits, "rejection_reasons": rejection_reasons,
        "audit_rejection_reasons": rejection_reasons,
        "evidence_warning": "all_archives_rejected_no_measurable_hit_rate" if counts["archives"] and counts["audit_rejected"] == counts["archives"] else None,
        "hit_rate_pct": {k: round(100 * v / counts["evaluated"], 2) if counts["evaluated"] else None for k, v in hits.items()},
        "roi": {k: {**v, "roi_pct": round(100 * v["return_yen"] / v["invested_yen"], 2) if v["invested_yen"] else None} for k, v in roi.items()},
        "roi_denominator": "verified_payout_only_not_all_evaluated_races",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("days", nargs="+")
    args = parser.parse_args()
    print(json.dumps(summary(args.days), ensure_ascii=False, sort_keys=True))
