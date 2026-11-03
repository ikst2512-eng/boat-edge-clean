"""Research-only stage attribution for absent hole shadow artifacts."""
import json
from pathlib import Path

def classify(stages,publication,shadow):
    if not isinstance(stages,dict):
        return "missing_stage_evidence"
    stage=stages.get("receipt_staging")
    outcome=publication.get("outcome") if isinstance(publication,dict) else None
    if stage=="failure" or outcome=="failed":
        return "publication_pipeline_failed"
    # A saved publication label cannot override a skipped, cancelled or
    # unknown staging outcome from the same workflow run.
    if stage!="success":
        return "publication_stage_not_successful"
    if outcome=="no_eligible_candidates":
        return "no_eligible_forecasts_published"
    if outcome!="pushed_to_main":
        return "publication_unverified"
    if not isinstance(shadow,dict):
        return "missing_shadow_evidence"
    if shadow.get("status")=="research_only_after_confirmed_push":
        records=shadow.get("records")
        if not isinstance(records,list):
            return "malformed_shadow_records"
        if any(not isinstance(r,dict) or
               not isinstance(r.get("race_code"),str) or
               not r.get("race_code") or
               r.get("status")!="shadow_frozen_unverified"
               for r in records):
            return "malformed_shadow_records"
        if records:
            return "research_shadow_available_unverified"
        return "published_but_no_eligible_freeze"
    return "published_but_shadow_missing_or_invalid"

def audit_directory(path):
    path=Path(path)
    if path.is_symlink() or not path.is_dir():
        return {"status":"missing_capture_artifact","formal":False}
    evidence=path/"four-mode-evidence"
    def read(filename):
        p=evidence/filename
        if not p.is_file() or p.is_symlink() or p.stat().st_size>2000000:
            return None
        try:return json.loads(p.read_text(encoding="utf-8"))
        except (OSError,ValueError,UnicodeError):return None
    stages=read("stages.json");publication=read("publication.json");shadow=read("hole-shadow.json")
    return {"schema":"HOLE_SHADOW_STAGE_VERDICT_V1",
            "status":classify(stages,publication,shadow),
            "publication_outcome":publication.get("outcome") if isinstance(publication,dict) else None,
            "source_capture":stages.get("source_capture") if isinstance(stages,dict) else None,
            "receipt_staging":stages.get("receipt_staging") if isinstance(stages,dict) else None,
            "formal":False,"production_forecast_changed":False,
            "independent_first_receipt_verified":False,
            "warning":"Research diagnostic only; local frozen evidence does not independently prove predeadline publication."}
