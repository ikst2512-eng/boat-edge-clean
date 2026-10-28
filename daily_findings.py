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
    whole=summary["all"]
    selected=summary["confidence_70"]
    if selected["races"] and whole["races"]:
        delta=round(selected["hit_rate_pct"]-whole["hit_rate_pct"],2)
        observation=f"保存済み検証では70%以上の的中率と全件の差は{delta:+.2f}ポイント（対象{selected['races']}件／全件{whole['races']}件）。将来の効果は未証明。"
    else:
        observation="比較に必要な検証済みレースがありません。傾向の評価は保留します。"
    if selected["roi_pct"] is None:
        roi_note="選別対象がないため回収率は未算出です。"
    elif selected["roi_pct"]<100:
        roi_note=f"70%以上の想定回収率は{selected['roi_pct']:.2f}%で、利益は実証できていません。"
    else:
        roi_note=f"70%以上の想定回収率は{selected['roi_pct']:.2f}%ですが、過去の標本内結果だけでは将来の利益を保証できません。"
    return {"schema":"CLEAN_DAILY_FINDINGS_V1","title":"検証ノート",
      "latest_verified_sample":data["sample_races"],"minimum_confidence":0.7,
      "post_policy_verified_races":data["cohorts"]["post_policy"]["all"]["races"],
      "all_races":{"races":summary["all"]["races"],"hit_rate_pct":summary["all"]["hit_rate_pct"],"roi_pct":summary["all"]["roi_pct"]},
      "confidence_70":{"races":summary["confidence_70"]["races"],"hit_rate_pct":summary["confidence_70"]["hit_rate_pct"],"roi_pct":summary["confidence_70"]["roi_pct"]},
      "findings":[{"kind":"観測結果","text":observation},
                  {"kind":"観測結果","text":roi_note},
                  {"kind":"未検証","text":"70%ルール確定後の保存予想と確定結果が十分に揃うまで、将来の改善は未証明です。"}],
      "recent_days":entries,"research_only":True}
