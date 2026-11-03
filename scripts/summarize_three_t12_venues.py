"""Aggregate research-only official T12 receipts, never certify original bytes or forecasts."""
import argparse
import json
from datetime import datetime
from pathlib import Path

def aggregate(root):
    root = Path(root)
    paths = sorted(root.glob("*/reports/three_originals.json"))
    if len(paths) > 24:
        raise ValueError("unexpected observation count")
    races = set()
    rows = []
    for path in paths:
        report = json.loads(path.read_text(encoding="utf-8"))
        race = report.get("race_code")
        if (not isinstance(race, str) or len(race) != 12 or not race.isdigit()
                or race in races
                or report.get("forecast_usable") is not False
                or report.get("full_t12_source_certified") is not False):
            raise ValueError("invalid, conflicting or duplicate race evidence")
        races.add(race)
        status = report.get("status")
        audit = report.get("audit")
        result = {"race_code": race, "observation_status": status,
                  "research_complete": False, "t12_margin_seconds": None,
                  "missing_components": [], "full_t12_source_certified": False,
                  "forecast_usable": False}
        if isinstance(audit, dict):
            if (audit.get("race_code") != race
                    or audit.get("forecast_usable") is not False
                    or audit.get("full_t12_source_certified") is not False):
                raise ValueError("audit identity or forecast certificate conflict")
            checks = audit.get("component_checks")
            missing = audit.get("missing_components")
            if (not isinstance(checks, dict) or not checks
                    or any(type(value) is not bool for value in checks.values())
                    or missing != [key for key, value in checks.items() if not value]):
                raise ValueError("contradictory component checks")
            complete = all(checks.values())
            if ((status == "research_components_complete_by_t12") is not complete
                    or audit.get("all_research_components_observed_by_t12") is not complete):
                raise ValueError("contradictory research completion")
            cutoff = datetime.fromisoformat(audit["cutoff_jst"])
            times = [datetime.fromisoformat(audit[key])
                     for key in ("racelist_received_jst", "beforeinfo_received_jst",
                                 "odds_received_jst")]
            if any(t.utcoffset() != cutoff.utcoffset() or
                   t.strftime("%Y%m%d") != race[:8] for t in times):
                raise ValueError("invalid observation dates")
            margin = (cutoff - max(times)).total_seconds()
            if complete and margin < 0:
                raise ValueError("late original incorrectly marked complete")
            result["t12_margin_seconds"] = round(margin, 3)
            result["missing_components"] = missing
            result["research_complete"] = complete
            result["official_deadline_jst"] = audit.get("official_deadline_jst")
        elif status in ("research_components_complete_by_t12", "research_components_incomplete"):
            raise ValueError("successful observation missing audit")
        rows.append(result)
    return {
        "observation_reports": len(rows),
        "research_complete_count": sum(row["research_complete"] for row in rows),
        "incomplete_or_unresolved_count": sum(not row["research_complete"] for row in rows),
        "scope": "same-run observation report declarations, not independent source ZIP re-audit",
        "full_t12_source_certified": False,
        "forecast_usable": False,
        "races": sorted(rows, key=lambda row: row["race_code"]),
    }


def markdown(summary):
    out = ["## 複数会場｜公式T−12研究観測結果", "",
           "※ 原本の再監査・最終進入認証・本番予想許可とは別。",
           f"- 保存された観測レポート：{summary['observation_reports']}件",
           f"- 研究用T−12充足：{summary['research_complete_count']}件",
           f"- 不完全・未判定：{summary['incomplete_or_unresolved_count']}件", "",
           "| レース | 研究用T−12 | 締切前の余裕(秒) | 未達項目 |",
           "|---|---|---:|---|"]
    for item in summary["races"]:
        remaining = item["t12_margin_seconds"]
        out.append(f"| {item['race_code']} | "
                   f"{'達成' if item['research_complete'] else item['observation_status']} | "
                   f"{remaining if remaining is not None else '未確認'} | "
                   f"{', '.join(item['missing_components']) or '-'} |")
    return "\n".join(out) + "\n"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", default="collected")
    p.add_argument("--output", default="reports/cross_venue_t12.json")
    args = p.parse_args()
    report = aggregate(args.root)
    dest = Path(args.output)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(markdown(report))
    import os
    if os.getenv("GITHUB_STEP_SUMMARY"):
        with Path(os.environ["GITHUB_STEP_SUMMARY"]).open("a") as summary:
            summary.write(markdown(report))


if __name__ == "__main__":
    main()
