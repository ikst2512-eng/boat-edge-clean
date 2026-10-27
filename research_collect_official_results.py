"""Opt-in, bounded official result retrieval for research diagnostics only.

No production writes, no saved forecast modification, no formal scoring.
Every capture is explicitly marked unverified until independent review.
"""
import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from research_official_result_parser import parse_result

BASE="https://www.boatrace.jp/owpc/pc/race/raceresult"
def collect(snapshot_dir, max_races=24):
    if not 1 <= max_races <= 144:
        raise ValueError("bounded collection required")
    report={"status":"UNVERIFIED_OFFICIAL_RESULT_COLLECTION","results":[],"failures":[]}
    selected = []
    for path in sorted(Path(snapshot_dir).glob("*.json")):
        try:
            obj = json.loads(path.read_text(encoding="utf-8"))
            required = ("race_code", "predictions", "generated_at", "cutoff_jst",
                        "source_deadline_jst", "model_git_sha", "input_sha256",
                        "source_title_sha256", "source_cards_sha256")
            if (obj.get("race_code") == path.stem and obj.get("status") == "research"
                    and obj.get("validated") is False and all(obj.get(k) for k in required)):
                selected.append(path)
        except (ValueError, OSError, TypeError, AttributeError):
            continue
    report["local_metadata_candidates"] = len(selected)
    for path in selected[:max_races]:
        key=path.stem
        if not re.fullmatch(r"20[0-9]{6}(?:0[1-9]|1[0-9]|2[0-4])(?:0[1-9]|1[0-2])",key):
            report["failures"].append({"race_code":key,"reason":"invalid_race_code"})
            continue
        url=f"{BASE}?hd={key[:8]}&jcd={key[8:10]}&rno={int(key[10:])}"
        try:
            req=Request(url,headers={"User-Agent":"BOAT-EDGE-CLEAN-RESEARCH/1.0","Accept":"text/html"})
            with urlopen(req,timeout=10) as response:
                if response.status != 200 or "html" not in response.headers.get("Content-Type","").lower():
                    raise ValueError("not_html_response")
                data=response.read(1_500_001)
            if len(data)>1_500_000:
                raise ValueError("oversized_response")
            result=parse_result(data.decode("utf-8"),url)
            result["fetched_at_utc"]=datetime.now(timezone.utc).isoformat()
            report["results"].append(result)
        except (ValueError,TimeoutError,OSError,UnicodeDecodeError) as exc:
            report["failures"].append({"race_code":key,"reason":type(exc).__name__})
    report["fetched"]=len(report["results"])
    report["failed"]=len(report["failures"])
    report["not_attempted"] = max(0, len(selected)-max_races)
    return report

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--snapshots",default="research_snapshots")
    p.add_argument("--limit",type=int,default=24)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    output=Path(a.output)
    if output.exists():
        raise ValueError("refuse overwrite existing result manifest")
    output.write_text(json.dumps(collect(a.snapshots,a.limit),ensure_ascii=False,indent=2),encoding="utf-8")
