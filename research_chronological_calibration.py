"""Chronological, read-only research model calibration. Never edits frozen forecasts.

Offline candidate selection only; never claims official/live hit-rate.
"""
import argparse
import json
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

from research_model import probabilities

ROOT = Path(__file__).resolve().parent
BETAS = (0.0, 0.2, 0.4, 0.6, 0.8, 1.0, 1.2)


def load_pairs(root=ROOT):
    rows = []
    for p in sorted((root / "research_snapshots").glob("*.json")):
        if p.is_symlink() or p.stat().st_size > 20000 or len(p.stem) != 12 or not p.stem.isdigit():
            continue
        result_path = root / "confirmed_results" / p.name
        if not result_path.is_file() or result_path.is_symlink() or result_path.stat().st_size > 20000:
            continue
        try:
            forecast = json.loads(p.read_text(encoding="utf-8"))
            result = json.loads(result_path.read_text(encoding="utf-8"))
            code = p.stem
            if forecast.get("race_code") != code or forecast.get("status") != "research" or forecast.get("validated") is not False:
                continue
            if result.get("race_code") != code or result.get("status") != "confirmed":
                continue
            generated = datetime.fromisoformat(forecast["generated_at"])
            cutoff = datetime.fromisoformat(forecast["cutoff_jst"])
            confirmed = datetime.fromisoformat(result["confirmed_at_jst"])
            deadline = datetime.fromisoformat(forecast["source_deadline_jst"])
            received = [datetime.fromisoformat(forecast[k]) for k in ("source_title_received_jst", "source_cards_received_jst")]
            if (any(x.utcoffset() != timedelta(hours=9) for x in (generated, cutoff, confirmed, deadline, *received))
                    or deadline - cutoff != timedelta(minutes=12)
                    or max(generated, *received) >= cutoff
                    or max(received) > generated
                    or deadline.strftime("%Y%m%d") != code[:8]
                    or not cutoff < deadline < confirmed):
                continue
            rates = forecast["national_win_rates"]
            order = result["finish_order"]
            if len(rates) != 6 or len(order) < 3 or len(set(order[:3])) != 3 or any(type(n) is not int or n not in range(1, 7) for n in order[:3]):
                continue
            probabilities(rates)
            ticket = tuple(order[:3])
            rows.append((code, rates, ticket))
        except (ValueError, KeyError, TypeError, OSError):
            continue
    return rows


def metrics(rows, beta):
    if not rows:
        return None
    hits = {3: 0, 5: 0, 10: 0}
    for _, rates, actual in rows:
        ranked = [t for t, _ in probabilities(rates, beta)]
        for k in hits:
            hits[k] += actual in ranked[:k]
    return {"races": len(rows), **{f"top{k}": hits[k] / len(rows) for k in hits}}


def report(rows, min_train=30, min_test=20):
    dates = sorted({code[:8] for code, _, _ in rows})
    if len(dates) < 2:
        return {"status": "insufficient_chronological_days", "races": len(rows)}
    # Reserve last chronological day: never tune a candidate using its holdout results.
    holdout_date = dates[-1]
    train = [r for r in rows if r[0][:8] < holdout_date]
    holdout = [r for r in rows if r[0][:8] == holdout_date]
    if len(train) < min_train or len(holdout) < min_test:
        return {"status": "insufficient_split", "train": len(train), "holdout": len(holdout), "holdout_date": holdout_date}
    scores = {beta: metrics(train, beta) for beta in BETAS}
    # Maximize training Top10 hit-rate, deterministic conservative beta tie break.
    winner = min(BETAS, key=lambda b: (-scores[b]["top10"], abs(b - 0.4), b))
    return {
        "status": "research_backtest_only",
        "train_races": len(train), "holdout_races": len(holdout),
        "holdout_date": holdout_date, "selected_beta": winner,
        "train_selected": scores[winner], "holdout_selected": metrics(holdout, winner),
        "holdout_baseline_beta_0_4": metrics(holdout, 0.4),
        "note": "Exploratory, not audited first-Git-add; no automatic deployment or live-forecast performance claim.",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-train", type=int, default=30)
    parser.add_argument("--min-test", type=int, default=20)
    args = parser.parse_args()
    print(json.dumps(report(load_pairs(), args.min_train, args.min_test), ensure_ascii=False, indent=2))
