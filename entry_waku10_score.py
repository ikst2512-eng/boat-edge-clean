"""Score only immutable, matched Waku10 course research records.

This is an exploratory paired evaluation, never a formal recommendation.
GitHub branch bytes and timestamps are not independent first-publication
certification. Source results arrive AFTER race cutoff and are never passed
into pilot generation. No archived forecast is created, changed or deleted.
"""
from collections import Counter
from datetime import datetime, timezone
from itertools import permutations
from pathlib import Path
from urllib.request import Request,urlopen
import csv
import hashlib
import io
import json
import re

from entry_waku10_durable_ledger import validate_waku10_archive, _at

VALID={"-".join(map(str,p)) for p in permutations(range(1,7),3)}
MODES=("baseline","waku10_course","waku10_course_plus_frame_st_proxy")
TOPS=(3,5,10)
ROOT="https://boatracecsv.github.io/data/results/realtime/"
FORWARD_FROM="20261104"


def _read_results(day,fetch=None,clock=None):
    if not re.fullmatch("20[0-9]{6}",day):
        raise ValueError("score_invalid_day")
    url=f"{ROOT}{day[:4]}/{day[4:6]}/{day[6:8]}.csv"
    if fetch is None:
        def fetch(url):
            with urlopen(Request(url,headers={"User-Agent":"BOAT-EDGE-CLEAN-RESEARCH/1.0"}),timeout=8) as response:
                if response.status!=200:
                    raise ValueError("score_result_http_invalid")
                return response.read(2_000_001)
    data=fetch(url)
    received=(clock or (lambda:datetime.now(timezone.utc)))()
    if received.utcoffset() is None or not isinstance(data,bytes) or len(data)>2_000_000:
        raise ValueError("score_results_invalid")
    try:
        reader=csv.DictReader(io.StringIO(data.decode("utf-8-sig")))
        if not reader.fieldnames or not {"レースコード","取得日時","1着_艇番","2着_艇番","3着_艇番"}.issubset(reader.fieldnames):
            raise ValueError("score_results_schema_invalid")
        rows=list(reader)
    except (UnicodeError,csv.Error) as exc:
        raise ValueError("score_results_unreadable") from exc
    counts=Counter(row.get("レースコード") for row in rows)
    matched={row["レースコード"]:row for row in rows
             if counts[row.get("レースコード")]==1}
    return matched, {"url":url,"sha256":hashlib.sha256(data).hexdigest(),
                      "received_at":received.isoformat(),
                      "duplicate_race_codes":sum(v-1 for v in counts.values() if v>1)}


def evaluate_waku10_archives(root, day, *, result_fetch=None, clock=None):
    """Scores the exact same 120-ticket cohort across three research modes."""
    if not re.fullmatch("20[0-9]{6}",day):
        raise ValueError("score_invalid_day")
    folder=Path(root)/"waku10"/day
    stats={name:{n:{"hits":0,"races":0,"hit_rate":None} for n in TOPS}
           for name in MODES}
    paired=0
    exclusions=Counter()
    included=[]
    candidates=[]
    if folder.is_dir():
        for path in sorted(folder.glob("*.json")):
            code=path.stem
            if (not re.fullmatch("20[0-9]{10}",code) or code[:8]!=day
                    or path.is_symlink() or path.stat().st_size>120_000):
                exclusions["invalid_path_or_oversize"]+=1
                continue
            try:
                raw=path.read_bytes()
                value=json.loads(raw)
                wrote=_at(value.get("write_received_at"))
                if not wrote or validate_waku10_archive(raw,now=wrote)!=f"waku10/{day}/{code}.json":
                    raise ValueError("score_invalid_archive")
            except (OSError,ValueError,TypeError,UnicodeError,KeyError):
                exclusions["invalid_or_unverified_archive"]+=1
                continue
            candidates.append(value)
    if candidates:
        results, result_source=_read_results(day,fetch=result_fetch,clock=clock)
    else:
        results={}
        result_source=None
    for value in candidates:
        code=value["race_code"]
        r=results.get(code)
        if r is None:
            exclusions["result_unavailable"]+=1
            continue
        reported=_at(r.get("取得日時"))
        cutoff=_at(value["cutoff_at"])
        if not reported or not cutoff or reported<=cutoff:
            exclusions["result_not_post_cutoff"]+=1
            continue
        try:
            outcome="-".join(str(int(r[f"{n}着_艇番"])) for n in (1,2,3))
        except (ValueError,TypeError,KeyError):
            exclusions["bad_result"]+=1
            continue
        if outcome not in VALID:
            exclusions["bad_result"]+=1
            continue
        paired+=1
        included.append(code)
        for name in MODES:
            for n in TOPS:
                stats[name][n]["hits"]+=outcome in value[name][:n]
    for name in MODES:
        for n in TOPS:
            stats[name][n]["races"]=paired
            stats[name][n]["hit_rate"]=round(stats[name][n]["hits"]/paired,6) if paired else None
    deltas={}
    for name in MODES[1:]:
        deltas[name]={n:{"net_hits":stats[name][n]["hits"]-stats["baseline"][n]["hits"]}
                      for n in TOPS}
    return {"schema":"waku10-matched-hits-diagnostic-v1",
            "day":day,"archive_files_eligible_for_scoring":len(candidates),
            "paired_races":paired,"paired_race_codes":included,
            "excluded":dict(exclusions),
            "topn":{name:{"Top"+str(n):stats[name][n] for n in TOPS}
                    for name in MODES},
            "net_vs_baseline":{name:{"Top"+str(n):deltas[name][n] for n in TOPS}
                               for name in deltas},
            "result_source_receipt":result_source,
            "forward_date_separated":day>=FORWARD_FROM,
            "research_only":True,"formal":False,
            "production_forecast_changed":False,
            "independent_remote_first_seen_verified":False,
            "independent_holdout_verified":False,
            "model_accuracy_improvement_proven":False}


def main():
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--ledger-root",default="entry-course-ledger")
    p.add_argument("--day",default=datetime.now(timezone.utc).strftime("%Y%m%d"))
    p.add_argument("--output",default="entry-course-evidence/waku10-score.json")
    args=p.parse_args()
    report=evaluate_waku10_archives(args.ledger_root,args.day)
    path=Path(args.output)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2)+"\n",
                    encoding="utf-8")
    print("WAKU10_MATCHED_RESEARCH_SCORE="+json.dumps(report,ensure_ascii=False,sort_keys=True))

if __name__=="__main__":
    main()
