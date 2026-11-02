"""Produce a reusable, non-certifying evidence report for archived late previews."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from scripts.audit_late_preview_evidence import audit

def report(root):
    root=Path(root)
    result=audit(root)
    status=("evidence_root_missing" if not root.is_dir() else
            "no_archived_race_records" if result["records"]==0 else
            "research_evidence_present_not_forecast_certified")
    return {"verification_status":status,
            "source_root":str(root),
            "archived_records_found":result["records"]>0,
            "audit":result,
            "note":"An empty archive is not zero collection failures or proof of T-12 success."}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",default="late_preview_evidence")
    ap.add_argument("--output",required=True)
    args=ap.parse_args()
    payload=report(args.root)
    path=Path(args.output)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"verification_status={payload['verification_status']} records={payload['audit']['records']}")

if __name__=="__main__":
    main()
