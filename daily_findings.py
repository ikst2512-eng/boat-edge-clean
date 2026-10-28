"""Daily findings computed from frozen confirmed predeadline forecasts.

Observations are descriptive, never auto-generated claims of discovery.
"""
from collections import defaultdict
from selection_dual import report

def daily_findings(root=None):
    data=report(root) if root is not None else report()
    days=defaultdict(list)
    # The API contains latest 24 race audit rows; full-day figures use ledger
    # totals only when all verified races share the same race date.
    for r in data["recent_verified_races"]:
        days[r["race_code"][:8]].append(r)
    all_dates={r["race_code"][:8] for r in data["recent_verified_races"]}
    entries=[]
    for day in sorted(days,reverse=True):
        records=days[day]
        entries.append({"date":f"{day[:4]}-{day[4:6]}-{day[6:]}",
          "sampled_verified_races":len(records),
          "candidate_races":sum(r["selection"]=="candidate" for r in records),
          "skipped_races":sum(r["selection"]=="skip" for r in records),
          "sample_only":True})
    summary=data["ledgers"]
    return {"schema":"CLEAN_DAILY_FINDINGS_V1","title":"検証ノート",
      "latest_verified_sample":data["sample_races"],"minimum_confidence":0.7,
      "post_policy_verified_races":data["cohorts"]["post_policy"]["all"]["races"],
      "all_races":{"races":summary["all"]["races"],"hit_rate_pct":summary["all"]["hit_rate_pct"],"roi_pct":summary["all"]["roi_pct"]},
      "confidence_70":{"races":summary["confidence_70"]["races"],"hit_rate_pct":summary["confidence_70"]["hit_rate_pct"],"roi_pct":summary["confidence_70"]["roi_pct"]},
      "findings":[{"kind":"観測結果","text":"信頼度70%以上は全レースより的中率が高いかを継続比較。回収率100%未満なら利益を実証したとは扱いません。"},
                  {"kind":"未検証","text":"70%ルール確定後の保存予想と確定結果が十分に揃うまで、将来の改善は未証明です。"}],
      "recent_days":entries,"research_only":True}
