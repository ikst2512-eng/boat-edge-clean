"""Read-only daily candidate archive from saved pre-race Git files.

Each candidate is retained by race code after its deadline. The API only reads
files already deployed from Git; it never predicts, selects retrospectively, or
modifies a saved forecast/result. Incomplete or invalid source files remain
visible as unverified rows rather than silently disappearing.
"""
import json
import re
from datetime import datetime, timedelta
from pathlib import Path

from evaluate_clean_prospective_cohort import independently_verified_payout
from research_model import probabilities
from selection_dual import MINIMUM_CONFIDENCE

ROOT = Path(__file__).resolve().parent
JST = timedelta(hours=9)
RACE_SUFFIX = r"(0[1-9]|1[0-9]|2[0-4])(0[1-9]|1[0-2])"
TICKET = re.compile(r"^[1-6]-[1-6]-[1-6]$")

# Existing candidate archives contain a 6-racer national-win-rate research
# model, not source-matched official exhibition, final entry, or water evidence.
# These IDs denote evidence absent from THIS stored candidate record; an
# external service may have the data, but it cannot be retroactively attributed
# to this immutable forecast. No inferred "buy" verdict is permitted.
REVIEW_MISSING = (
    "official_exhibition_six",
    "start_exhibition_entry_st",
    "course_2_wall_escape",
    "wind_waves_water",
    "odds_120_before_cutoff",
    "independent_first_seen_and_formal_attestation",
)



def _jst(value):
    if not isinstance(value, str) or not value.endswith("+09:00"):
        raise ValueError("invalid JST time")
    moment = datetime.fromisoformat(value)
    if moment.utcoffset() != JST:
        raise ValueError("invalid timezone")
    return moment


def _read_record(path, max_bytes):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > max_bytes:
        raise ValueError("unsafe archive")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("invalid archive")
    return data


def _research_selection(data):
    """Read-only 70% *model head mass* research signal, never a purchase verdict.

    Reuse the existing selection_dual policy on the exact saved model inputs.
    Missing/incompatible pre-race data stays unassessed; never use results.
    """
    unassessed = {"selection_status": "unassessed", "head_top2_model_pct": None}
    if data.get("model_version") != "clean-prospective-national-beta0.4-v1":
        return unassessed
    try:
        board = probabilities(data.get("national_win_rates"))
        masses = [sum(p for ticket, p in board if ticket[0] == boat) for boat in range(1, 7)]
        signal = sum(sorted(masses, reverse=True)[:2])
    except (ValueError, TypeError, ArithmeticError):
        return unassessed
    return {
        "selection_status": "research_70_pass" if signal >= MINIMUM_CONFIDENCE else "research_70_below",
        "head_top2_model_pct": round(100 * signal, 2),
    }


def _candidate(path, code):
    data = _read_record(path, 30000)
    tickets = data.get("predictions")
    generated = _jst(data["generated_at"])
    deadline = _jst(data["source_deadline_jst"])
    cutoff = _jst(data["cutoff_jst"])
    title_received = _jst(data["source_title_received_jst"])
    cards_received = _jst(data["source_cards_received_jst"])
    if (data.get("race_code") != code or data.get("status") != "prospective_candidate"
            or data.get("formal") is not False or data.get("scoring") is not False
            or data.get("validated") is not False
            or deadline.strftime("%Y%m%d") != code[:8]
            or deadline - cutoff != timedelta(minutes=12)
            or not (title_received <= generated and cards_received <= generated < cutoff)
            or not isinstance(tickets, list) or not 1 <= len(tickets) <= 10
            or len(tickets) != len(set(tickets))):
        raise ValueError("unverified candidate")
    if any(not isinstance(t, str) or not TICKET.fullmatch(t)
           or len(set(t.split("-"))) != 3 for t in tickets):
        raise ValueError("invalid ticket")
    return {
        "forecast_status": "saved_research_unattested",
        "generated_at_jst": data["generated_at"],
        "deadline_jst": data["source_deadline_jst"],
        "tickets": tickets,
        "model_version": str(data.get("model_version", ""))[:100],
        "research_input_received_jst": max(title_received, cards_received).isoformat(),
        "purchase_review_status": "hold_evidence_not_attested",
        "purchase_review_missing": list(REVIEW_MISSING),
        **_research_selection(data),
    }


def _confirmed(path, code):
    if not path.exists() and not path.is_symlink():
        return {"result_status": "pending", "finish": None}
    try:
        data = _read_record(path, 10000)
        finish = data.get("finish_order")
        received = _jst(data["collected_at_jst"])
        confirmed = _jst(data["confirmed_at_jst"])
        if (data.get("race_code") != code or data.get("status") != "confirmed"
                or not isinstance(finish, list) or len(finish) != 3
                or any(type(x) is not int or x not in range(1, 7) for x in finish)
                or len(set(finish)) != 3 or received < confirmed
                or not isinstance(data.get("source_url"), str)
                or not data["source_url"].startswith("https://")):
            raise ValueError("unverified result")
        return {
            "result_status": "confirmed_archive",
            "finish": "-".join(str(x) for x in finish),
            "collected_at_jst": data["collected_at_jst"],
        }
    except (ValueError, TypeError, KeyError, OSError, OverflowError):
        return {"result_status": "unverified", "finish": None}


def daily_candidate_history(day, root=ROOT):
    """Return all saved candidate race keys for a requested day, never only upcoming."""
    if not isinstance(day, str) or not re.fullmatch(r"20\d{6}", day):
        return 400, {"ok": False, "status": "invalid_date"}
    try:
        datetime.strptime(day, "%Y%m%d")
    except ValueError:
        return 400, {"ok": False, "status": "invalid_date"}
    root = Path(root)
    predictions = root / "prospective_predictions"
    results = root / "confirmed_results"
    rows = []
    for path in sorted(predictions.glob(day + "????.json")):
        code = path.stem
        if not re.fullmatch(day + RACE_SUFFIX, code):
            continue
        row = {
            "race_code": code,
            "venue": int(code[8:10]),
            "race": int(code[10:12]),
            "forecast_status": "unverified",
            "selection_status": "unassessed",
            "head_top2_model_pct": None,
            "research_input_received_jst": None,
            "purchase_review_status": "unassessed",
            "purchase_review_missing": list(REVIEW_MISSING),
            "tickets": [],
            "deadline_jst": None,
        }
        try:
            row.update(_candidate(path, code))
        except (ValueError, TypeError, KeyError, OSError, OverflowError):
            pass
        row.update(_confirmed(results / (code + ".json"), code))
        # Payouts are independent results evidence, never inferred from odds,
        # forecasts, or the winning ticket. Fail closed if either saved source
        # is missing, malformed, or inconsistent with the confirmed finish.
        row["payout_status"] = "unverified"
        row["payout_yen_per_100"] = None
        if row["result_status"] == "confirmed_archive":
            payout = independently_verified_payout(code, root)
            if payout is not None and payout[0] == row["finish"]:
                row["payout_status"] = "verified_independent"
                row["payout_yen_per_100"] = payout[1]
        rows.append(row)
    rows.sort(key=lambda r: (r["deadline_jst"] or "9999", r["race_code"]))
    return 200, {
        "ok": True,
        "schema": "CLEAN_CANDIDATE_HISTORY_V1",
        "date": day,
        "source": "git_deployed_pre_race_archives",
        "coverage": "deployed_files_only",
        "first_git_add_verified": False,
        "production_forecast": False,
        "candidate_count": len(rows),
        "selection_rule": "top2_head_mass_ge_70_research_only_v1",
        "research_70_pass_count": sum(r["selection_status"] == "research_70_pass" for r in rows),
        "research_70_below_count": sum(r["selection_status"] == "research_70_below" for r in rows),
        "research_unassessed_count": sum(r["selection_status"] == "unassessed" for r in rows),
        "purchase_review_schema": "candidate_evidence_hold_v1",
        "purchase_review_approved_count": 0,
        "research_forecast_count": sum(r["forecast_status"] == "saved_research_unattested" for r in rows),
        "confirmed_result_count": sum(r["result_status"] == "confirmed_archive" for r in rows),
        "payout_verified_count": sum(r["payout_status"] == "verified_independent" for r in rows),
        "races": rows,
    }
