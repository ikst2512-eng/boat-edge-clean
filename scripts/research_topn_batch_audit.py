"""Research-only batch audit of already stored forecasts and confirmed results."""
import json
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
    for race_code in sorted(forecast_paths.keys() & result_paths.keys()):
        try:
            forecast = json.loads(forecast_paths[race_code].read_text(encoding="utf-8"))
            result = json.loads(result_paths[race_code].read_text(encoding="utf-8"))
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
            for n in (3, 5, 10):
                stats[f"top{n}"] += int(0 < position <= n)
        except (OSError, ValueError, KeyError, TypeError):
            stats["rejected"] += 1
    for n in (3, 5, 10):
        stats[f"top{n}_rate_pct"] = round(100 * stats[f"top{n}"] / stats["matched"], 2) if stats["matched"] else None
    return stats


if __name__ == "__main__":
    print(json.dumps({"scope": "research_only_not_formal", "counts": run()}, ensure_ascii=False, indent=2))
