"""Research-only batch audit of already stored forecasts and confirmed results."""
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run():
    forecasts = ROOT / "research_snapshots"
    results = ROOT / "confirmed_results"
    forecast_paths = {p.stem: p for p in forecasts.glob("*.json")}
    result_paths = {p.stem: p for p in results.glob("*.json")}
    stats = {"matched": 0, "top3": 0, "top5": 0, "top10": 0,
             "rejected": 0, "forecast_only": len(forecast_paths.keys() - result_paths.keys()),
             "result_only": len(result_paths.keys() - forecast_paths.keys())}
    mass_coverage = {"all_forecasts": len(forecast_paths), "with_topn_mass": 0, "without_topn_mass": 0, "invalid_topn_mass": 0}
    for path in forecast_paths.values():
        try:
            saved = json.loads(path.read_text(encoding="utf-8"))
            mass = saved.get("topn_model_mass_pct")
            if mass is None:
                mass_coverage["without_topn_mass"] += 1
            elif (isinstance(mass, dict) and all(isinstance(mass.get(str(n)), (int, float)) and not isinstance(mass[str(n)], bool) for n in (3, 5, 10)) and 0 < mass["3"] < mass["5"] < mass["10"] <= 100 and saved.get("confidence_calibrated") is False):
                mass_coverage["with_topn_mass"] += 1
            else:
                mass_coverage["invalid_topn_mass"] += 1
        except (OSError, ValueError, TypeError, AttributeError):
            mass_coverage["invalid_topn_mass"] += 1
    by_mass_cohort = {"with_topn_mass": {"matched": 0, "top3": 0, "top5": 0, "top10": 0}, "without_topn_mass": {"matched": 0, "top3": 0, "top5": 0, "top10": 0}}
    by_model = {}
    confidence_coverage = {"stored_numeric_confidence": 0, "missing_confidence": 0}
    for race_code in sorted(forecast_paths.keys() & result_paths.keys()):
        try:
            forecast = json.loads(forecast_paths[race_code].read_text(encoding="utf-8"))
            result = json.loads(result_paths[race_code].read_text(encoding="utf-8"))
            generated = datetime.fromisoformat(forecast["generated_at"])
            cutoff = datetime.fromisoformat(forecast["cutoff_jst"])
            source_deadline = datetime.fromisoformat(forecast["source_deadline_jst"])
            if (generated.tzinfo is None or cutoff.tzinfo is None or source_deadline.tzinfo is None
                or not generated < cutoff < source_deadline):
                raise ValueError("not_verified_predeadline_snapshot")
            tickets = forecast["predictions"]
            finish = result["finish_order"]
            if (forecast.get("race_code") != race_code or result.get("race_code") != race_code
                or forecast.get("status") != "research" or forecast.get("validated") is not False
                or result.get("status") != "confirmed" or len(tickets) != 10
                or len(set(tickets)) != 10 or len(finish) < 3
                or any(not isinstance(t, str) or len(t.split("-")) != 3
                       or len(set(t.split("-"))) != 3 for t in tickets)):
                raise ValueError("invalid pair")
            winning = "-".join(str(n) for n in finish[:3])
            position = tickets.index(winning) + 1 if winning in tickets else 0
            stats["matched"] += 1
            model = str(forecast.get("model_version") or "unknown")
            group = by_model.setdefault(model, {"matched": 0, "top3": 0, "top5": 0, "top10": 0})
            group["matched"] += 1
            mass = forecast.get("topn_model_mass_pct")
            cohort_name = "with_topn_mass" if (isinstance(mass, dict) and forecast.get("confidence_calibrated") is False and all(isinstance(mass.get(str(n)), (int, float)) and not isinstance(mass[str(n)], bool) for n in (3, 5, 10)) and 0 < mass["3"] < mass["5"] < mass["10"] <= 100) else "without_topn_mass"
            cohort = by_mass_cohort[cohort_name]
            cohort["matched"] += 1
            confidence = forecast.get("confidence_pct")
            if isinstance(confidence, (int, float)) and not isinstance(confidence, bool) and 0 <= confidence <= 100:
                confidence_coverage["stored_numeric_confidence"] += 1
            else:
                confidence_coverage["missing_confidence"] += 1
            for n in (3, 5, 10):
                hit = int(0 < position <= n)
                stats[f"top{n}"] += hit
                group[f"top{n}"] += hit
                cohort[f"top{n}"] += hit
        except (OSError, ValueError, KeyError, TypeError):
            stats["rejected"] += 1
    for n in (3, 5, 10):
        stats[f"top{n}_rate_pct"] = round(100 * stats[f"top{n}"] / stats["matched"], 2) if stats["matched"] else None
    for cohort in by_mass_cohort.values():
        for n in (3, 5, 10):
            cohort[f"top{n}_rate_pct"] = round(100 * cohort[f"top{n}"] / cohort["matched"], 2) if cohort["matched"] else None
    return {"by_mass_cohort": by_mass_cohort, "counts": stats, "by_model": by_model, "confidence_coverage": confidence_coverage, "mass_coverage": mass_coverage,
            "confidence_70_pct_selection": "not_computed_without_verified_pre_race_confidence"}


if __name__ == "__main__":
    print(json.dumps({"scope": "research_only_not_formal", "audit": run()}, ensure_ascii=False, indent=2))
