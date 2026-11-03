"""Render research-only official T12 observation for GitHub Actions summary."""
import argparse
import json
from pathlib import Path

CHECK_LABELS = {
    "racecard_original_hash_verified": "出走表原本SHA256",
    "racecard_six_registrations": "登録番号6艇",
    "racer_registration_ids_match": "出走表・直前JSONの登録番号一致",
    "racecard_received_by_t12": "出走表T−12受信",
    "beforeinfo_received_by_t12": "公式直前T−12受信",
    "beforeinfo_six_unique_boats": "公式直前6艇番号の重複なし",
    "exhibition_six_courses": "展示進入6コース",
    "exhibition_times_six": "展示タイム6艇",
    "tilt_six": "チルト6艇",
    "start_exhibition_six": "展示ST6艇",
    "odds_120": "3連単120通り",
    "odds_received_by_t12": "オッズT−12受信",
}


def summarize(data):
    if not isinstance(data, dict):
        raise ValueError("invalid observation")
    race = data.get("race_code")
    if not isinstance(race, str) or len(race) != 12 or not race.isdigit():
        raise ValueError("invalid race identity")
    status = str(data.get("status", "unknown"))
    result = ["## 公式3原本 T−12研究観測", "",
              f"- レース: `{race}`",
              f"- 観測結果: `{status}`",
              "- 本番予想の使用許可: **なし**",
              "- 実進入確定・T−12完全認証: **未認証**", ""]
    if data.get("forecast_usable") is not False or data.get("full_t12_source_certified") is not False:
        raise ValueError("unexpected forecast certification in research report")
    audit = data.get("audit")
    if not isinstance(audit, dict):
        result.append("公式3原本の独立監査は未完了。欠落元データを完全合格として数えない。")
        for field in ("beforeinfo_status", "racecard_status", "odds_status", "cutoff_jst"):
            if data.get(field) is not None:
                result.append(f"- {field}: `{data[field]}`")
        return "\n".join(result) + "\n"
    if audit.get("race_code") != race or audit.get("full_t12_source_certified") is not False:
        raise ValueError("audit identity or certification mismatch")
    result += [f"- 公式締切: `{audit.get('official_deadline_jst', '未確認')}`",
               f"- T−12基準: `{audit.get('cutoff_jst', '未確認')}`",
               f"- 最終原本受信: `{audit.get('latest_original_received_jst', '未確認')}`",
               f"- T−12までの最終受信余裕: `{audit.get('t12_receipt_margin_seconds', '未確認')}` 秒",
               "", "| 原本 | 受信時刻(JST) |", "|---|---|",
               f"| 出走表 | {audit.get('racelist_received_jst', '未確認')} |",
               f"| 公式直前 | {audit.get('beforeinfo_received_jst', '未確認')} |",
               f"| 3連単オッズ | {audit.get('odds_received_jst', '未確認')} |", ""]
    checks = audit.get("component_checks")
    if not isinstance(checks, dict) or set(checks) != set(CHECK_LABELS) or any(type(v) is not bool for v in checks.values()):
        raise ValueError("invalid component checks")
    missing = audit.get("missing_components")
    expected_missing = [key for key, value in checks.items() if not value]
    if missing != expected_missing:
        raise ValueError("contradictory missing-component report")
    complete = not expected_missing
    if audit.get("all_research_components_observed_by_t12") is not complete:
        raise ValueError("contradictory completeness")
    result += ["| 検証項目 | 結果 |", "|---|---|"]
    result += [f"| {CHECK_LABELS[key]} | {'確認済み' if checks[key] else '未達'} |" for key in CHECK_LABELS]
    result += ["", f"研究用3原本のT−12充足: **{'達成' if complete else '未達成'}**",
               "実進入確定・正式予想への使用許可は付与しない。"]
    return "\n".join(result) + "\n"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("input")
    p.add_argument("summary")
    args = p.parse_args()
    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    path = Path(args.summary)
    with path.open("a", encoding="utf-8") as f:
        f.write(summarize(data))


if __name__ == "__main__":
    main()
