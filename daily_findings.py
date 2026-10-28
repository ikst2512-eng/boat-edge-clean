"""Daily findings computed from frozen confirmed predeadline forecasts.

Observations are descriptive, never auto-generated claims of discovery.
"""
from selection_dual import report

def daily_findings(root=None):
    data=report(root) if root is not None else report()
    entries=[]
    for day,stats in sorted(data["verified_daily"].items(),reverse=True):
        all_races=stats["all"]
        selected=stats["confidence_70"]
        entries.append({"date":f"{day[:4]}-{day[4:6]}-{day[6:]}",
          "verified_races":all_races["races"],"candidate_races":selected["races"],
          "skipped_races":all_races["races"]-selected["races"],
          "all_hit_rate_pct":all_races["hit_rate_pct"],
          "candidate_hit_rate_pct":selected["hit_rate_pct"],
          "all_roi_pct":all_races["roi_pct"],"candidate_roi_pct":selected["roi_pct"],
          "sample_only":False})
    summary=data["ledgers"]
    return {"schema":"CLEAN_DAILY_FINDINGS_V1","title":"検証ノート",
      "latest_verified_sample":data["sample_races"],"minimum_confidence":0.7,
      "post_policy_verified_races":data["cohorts"]["post_policy"]["all"]["races"],
      "all_races":{"races":summary["all"]["races"],"hit_rate_pct":summary["all"]["hit_rate_pct"],"roi_pct":summary["all"]["roi_pct"]},
      "confidence_70":{"races":summary["confidence_70"]["races"],"hit_rate_pct":summary["confidence_70"]["hit_rate_pct"],"roi_pct":summary["confidence_70"]["roi_pct"]},
      "findings":[{"kind":"観測結果","text":"信頼度70%以上は全レースより的中率が高いかを継続比較。回収率100%未満なら利益を実証したとは扱いません。"},
                  {"kind":"未検証","text":"70%ルール確定後の保存予想と確定結果が十分に揃うまで、将来の改善は未証明です。"}],
      "recent_days":entries,"research_only":True}
