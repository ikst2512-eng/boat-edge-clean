"""One-shot read-only three-original observation; evidence only, never forecasts."""
import argparse
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from research_model import JST
from scripts.capture_official_beforeinfo_json import capture as before_capture
from scripts.capture_official_racelist_receipt import capture as racecard_capture
from scripts.capture_official_odds_receipt import capture as odds_capture
from scripts.audit_three_official_t12_originals import audit_three_originals


def observe(race_code, root, observation_id, *, now=None,
            before=before_capture, card=racecard_capture, odds=odds_capture,
            auditor=audit_three_originals):
    """Only observe on race day; fail closed without a verified deadline."""
    now = now or (lambda: datetime.now(JST))
    root = Path(root)
    if not isinstance(race_code, str) or not re.fullmatch(r"20[0-9]{10}", race_code):
        raise ValueError("invalid race code")
    if not isinstance(observation_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", observation_id):
        raise ValueError("invalid observation ID")
    day = race_code[:8]
    report = {"race_code": race_code, "status": "not_started",
              "t12_eligible": False, "forecast_usable": False,
              "full_t12_source_certified": False}
    if now().strftime("%Y%m%d") != day:
        report["status"] = "not_current_jst_race_day"
        return report
    a = before(race_code, root, "before" + observation_id)
    report["beforeinfo_status"] = a.get("status")
    if a.get("status") != "official_json_observed_not_t12_certified":
        report["status"] = "beforeinfo_source_unavailable"
        return report
    deadline_text = a.get("deadline_display")
    if not isinstance(deadline_text, str) or not re.fullmatch(r"(?:[01][0-9]|2[0-3]):[0-5][0-9]", deadline_text):
        report["status"] = "official_deadline_unavailable"
        return report
    deadline = datetime.fromisoformat(
        f"{day[:4]}-{day[4:6]}-{day[6:8]}T{deadline_text}:00+09:00")
    cutoff = deadline - timedelta(minutes=12)
    report["official_deadline_jst"] = deadline.isoformat()
    report["cutoff_jst"] = cutoff.isoformat()
    if (datetime.fromisoformat(a["received_at_jst"]) > cutoff
            or now() + timedelta(seconds=60) >= cutoff):
        report["status"] = "t12_preflight_expired"
        return report
    c = card(race_code, root, "card" + observation_id)
    report["racecard_status"] = c.get("status")
    if c.get("status") != "official_racelist_html_observed_research_only":
        report["status"] = "racecard_source_unavailable"
        return report
    if (datetime.fromisoformat(c["received_at_jst"]) > cutoff
            or now() + timedelta(seconds=25) >= cutoff):
        report["status"] = "t12_preflight_expired"
        return report
    o = odds(race_code, deadline.isoformat(), root, "odds" + observation_id)
    report["odds_status"] = o.get("status")
    if o.get("status") != "official_odds_observed_research_only":
        report["status"] = "odds_source_unavailable"
        return report
    base = root / "observations"
    locations = lambda prefix: base / (prefix + observation_id) / day / race_code
    try:
        audit = auditor(locations("card"), locations("before"), locations("odds"))
    except (ValueError, TypeError, KeyError, OSError, UnicodeError) as exc:
        report["status"] = "independent_source_audit_failed"
        report["audit_error_type"] = type(exc).__name__
        return report
    report["audit"] = audit
    report["status"] = ("research_components_complete_by_t12"
                        if audit["all_research_components_observed_by_t12"]
                        else "research_components_incomplete")
    return report


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--race-code", required=True)
    p.add_argument("--root", default="evidence")
    p.add_argument("--observation-id", required=True)
    p.add_argument("--report", default="reports/three_originals.json")
    args = p.parse_args()
    result = observe(args.race_code, args.root, args.observation_id)
    output = Path(args.report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    # A research observation with incomplete inputs is a valid diagnostic,
    # not evidence of full T12 certification; do not fail the upload step.
    if result["status"] not in ("research_components_complete_by_t12",
                                "research_components_incomplete"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
