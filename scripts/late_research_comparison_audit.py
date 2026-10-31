"""Read-only audit of whether late six-boat evidence can be compared with saved forecasts.

Never generates, rewrites, or retrospectively enriches a prediction.
"""
import json
from datetime import datetime
from pathlib import Path
from scripts.late_preview_feature_pairs import build


def audit(day, preview_root, repository_root):
    features=build(day,preview_root)
    root=Path(repository_root)
    rows=[]
    for pair in features["records"]:
        code=pair["race_code"]
        early_file=root/"research_snapshots"/(code+".json")
        result_file=root/"confirmed_results"/(code+".json")
        row={"race_code":code,"early_forecast":"missing",
             "confirmed_result":"missing","late_model_prediction":"not_generated"}
        if early_file.is_file():
            try:
                record=json.loads(early_file.read_text(encoding="utf-8"))
                generated=datetime.fromisoformat(record["generated_at"])
                received=datetime.fromisoformat(pair["both_sources_received_at_jst"])
                if (record.get("race_code")==code and record.get("status")=="research"
                        and generated.utcoffset() is not None and received.utcoffset() is not None):
                    row["early_forecast"]="valid"
                    row["preview_relative_to_early_forecast"]=(
                        "after" if received>generated else "before_or_equal")
                else:
                    row["early_forecast"]="invalid"
            except (ValueError, TypeError, KeyError, OSError, AttributeError):
                row["early_forecast"]="invalid"
        if result_file.is_file():
            try:
                result=json.loads(result_file.read_text(encoding="utf-8"))
                finish=result.get("finish_order")
                if (result.get("race_code")==code and result.get("status")=="confirmed"
                    and isinstance(finish,list) and len(finish)>=3
                    and all(type(n) is int and n in range(1,7) for n in finish[:3])
                    and len(set(finish[:3]))==3):
                    row["confirmed_result"]="valid"
                else:
                    row["confirmed_result"]="invalid"
            except (ValueError, TypeError, OSError, AttributeError):
                row["confirmed_result"]="invalid"
        rows.append(row)
    return {"day":day,"late_preview_pairs":features["ready_count"],
            "early_forecast_matches":sum(r["early_forecast"]=="valid" for r in rows),
            "confirmed_result_matches":sum(r["confirmed_result"]=="valid" for r in rows),
            "complete_comparison_cohort":sum(r["early_forecast"]=="valid" and r["confirmed_result"]=="valid" for r in rows),
            "late_model_forecasts":0,"rows":rows}


if __name__=="__main__":
    from research_model import JST
    day=datetime.now(JST).strftime("%Y%m%d")
    print(json.dumps(audit(day,Path("late_preview_evidence"),Path(".")),ensure_ascii=False))
