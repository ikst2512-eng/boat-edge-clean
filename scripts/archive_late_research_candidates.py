"""Archive prospective late research candidate predictions, never backfill.

Each file is created once, before the race deadline. Original early forecasts are untouched.
"""
import json
from datetime import datetime, timedelta
from pathlib import Path
from research_model import JST
from scripts.late_research_candidate import build_candidates


def archive(day, preview_root, output_root, now=None):
    now=now or datetime.now(JST)
    if now.utcoffset() is None:
        raise ValueError("timezone-aware generation required")
    candidates=build_candidates(day, preview_root)["predictions"]
    saved=[]
    skipped={"too_late":0,"existing":0,"invalid_source":0}
    for prediction in candidates:
        code=prediction["race_code"]
        try:
            source=json.loads((Path(preview_root)/day/"tkz"/(code+".json")).read_text(encoding="utf-8"))
            clock=source["source_row"]["締切時刻"]
            deadline=datetime.strptime(day+clock,"%Y%m%d%H:%M").replace(tzinfo=JST)
            received=datetime.fromisoformat(prediction["generated_from_received_at_jst"])
            if received.utcoffset() is None or received>now:
                skipped["invalid_source"]+=1
                continue
            if now>=deadline-timedelta(minutes=2):
                skipped["too_late"]+=1
                continue
            target=Path(output_root)/day/(code+".json")
            target.parent.mkdir(parents=True,exist_ok=True)
            record=dict(prediction,generated_at_jst=now.isoformat(),
                        race_deadline_jst=deadline.isoformat(),
                        archive_policy="prospective_only_before_deadline_minus_2min",
                        research_only=True)
            try:
                with target.open("x",encoding="utf-8") as file:
                    file.write(json.dumps(record,ensure_ascii=False,sort_keys=True))
            except FileExistsError:
                skipped["existing"]+=1
                continue
            saved.append(code)
        except (KeyError,ValueError,TypeError,OSError,AttributeError):
            skipped["invalid_source"]+=1
    return {"day":day,"upstream_candidate_count":len(candidates),
            "archive_state":"no_valid_preview_pairs" if not candidates else ("saved" if saved else "all_candidates_skipped"),
            "saved_count":len(saved),"saved_codes":saved,"skipped":skipped,
            "status":"isolated_prospective_research_not_published"}


if __name__=="__main__":
    print(json.dumps(archive(datetime.now(JST).strftime("%Y%m%d"),
                             Path("late_preview_evidence"),Path("late_research_candidates")),
                     ensure_ascii=False))
