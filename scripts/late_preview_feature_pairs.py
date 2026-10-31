"""Extract independently validated, same-race six-boat preview features for future research.

No predictions or backfilled historic inputs are made here.
"""
import json
import sys
from datetime import datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from scripts.collect_live_preview_evidence import paired_six_lane_coverage


def build(day, root, require_t12=False):
    coverage=paired_six_lane_coverage(day,root)
    verified=coverage["paired_12min_codes"] if require_t12 else coverage["paired_codes"]
    output=[]
    for code in verified:
        tkz=json.loads((Path(root)/day/"tkz"/(code+".json")).read_text(encoding="utf-8"))
        stt=json.loads((Path(root)/day/"stt"/(code+".json")).read_text(encoding="utf-8"))
        # Preserve original boat identities; entry course is a feature, not lane index.
        t=tkz["source_row"]
        s=stt["source_row"]
        boats=[{"boat":i,
                "exhibition_time":float(t[f"艇{i}_展示タイム"]),
                "tilt":float(t[f"艇{i}_チルト"]),
                "entry_course":int(s[f"艇{i}_コース"]),
                "start_exhibition":s[f"艇{i}_スタート展示"]}
               for i in range(1,7)]
        observed_at=max(datetime.fromisoformat(tkz["received_at_jst"]),
                        datetime.fromisoformat(stt["received_at_jst"]))
        output.append({"race_code":code,"boats":boats,
                       "both_sources_received_at_jst":observed_at.isoformat(),
                       "status":"verified_preview_features_not_prediction"})
    return {"date":day,"records":output,"ready_count":len(output),
            "timing_gate":"strict_t12_both_sources" if require_t12 else "late_t2_both_sources",
            "retrospective_only":True}


if __name__=="__main__":
    from research_model import JST
    day=datetime.now(JST).strftime("%Y%m%d")
    print(json.dumps(build(day,Path("late_preview_evidence")),ensure_ascii=False))
