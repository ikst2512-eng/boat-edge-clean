"""One-shot read/capture of predeadline preview CSV; local only, no git push."""
import json
import csv
import io
from datetime import datetime, timedelta
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from research_model import JST
from late_preview_capture import save_preview, KINDS, six_lane_status
from scripts.preview_timing_integrity import classify, parse_jst


def _late_row_reason(row, received, margin_minutes=2):
    """Explain a known late source without changing classify() eligibility."""
    if classify(row, received, margin_minutes=margin_minutes) != "too_late":
        return None
    deadline = parse_jst(row.get("締切時刻"))
    if deadline is None:
        code, hhmm = row.get("レースコード"), row.get("締切時刻")
        if isinstance(code, str) and len(code) == 12 and code.isascii() and code.isdigit() and isinstance(hhmm, str):
            try:
                deadline = datetime.strptime(code[:8] + hhmm, "%Y%m%d%H:%M").replace(tzinfo=JST)
            except ValueError:
                pass
    observed = parse_jst(row.get("取得日時"))
    if deadline is None or observed is None:
        return "late_reason_unverified"
    # A late source observation implies its HTTP receipt is late too; do
    # not misdiagnose that case as mere transport/scheduler delay.
    if observed >= deadline - timedelta(minutes=margin_minutes):
        return "source_and_http_late"
    return "http_receipt_late_only"
from scripts.collect_live_preview_evidence import paired_six_lane_coverage

BASE="https://boatracecsv.github.io/data/previews/"
def collect(day=None, root=None, fetch=None, clock=None):
    now=clock or (lambda:datetime.now(JST))
    day=day or now().strftime("%Y%m%d")
    if len(day)!=8 or not day.isascii() or not day.isdigit():
        raise ValueError("invalid date")
    datetime.strptime(day,"%Y%m%d")
    root=Path(root or "late_preview_evidence")
    report={"date":day,"status":"read_only_local_capture","kinds":{}}
    for kind in KINDS:
        url=f"{BASE}{kind}/{day[:4]}/{day[4:6]}/{day[6:]}.csv"
        started=now()
        try:
            if fetch:
                raw=fetch(url)
            else:
                with urlopen(Request(url,headers={"User-Agent":"BOAT-EDGE-CLEAN-RESEARCH/1.0"}),timeout=8) as response:
                    raw=response.read(3_000_001)
            received=now()
            elapsed_ms=max(0,round((received-started).total_seconds()*1000))
            rows=list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
            gate={"pre_cutoff_observed":0,"too_late":0,"unknown_time":0}
            early={"pre_cutoff_observed":0,"too_late":0,"unknown_time":0}
            six_lanes={"complete":0,"incomplete":0,"not_applicable":0}
            late_reasons={"source_and_http_late":0,"http_receipt_late_only":0,
                          "late_reason_unverified":0}
            late_samples=[]
            for row in rows:
                state=classify(row,received,margin_minutes=2)
                gate[state]+=1
                early[classify(row,received,margin_minutes=12)]+=1
                six_lanes[six_lane_status(kind,row)]+=1
                if state=="too_late":
                    reason=_late_row_reason(row,received,margin_minutes=2)
                    late_reasons[reason]+=1
                    if len(late_samples)<2:
                        late_samples.append({"race_code":row.get("レースコード"),
                            "deadline":row.get("締切時刻"),
                            "source_observed_at":row.get("取得日時"),
                            "http_received_at":received.isoformat(),"reason":reason})
            written=save_preview(raw,kind,day,received,root)
            report["kinds"][kind]={"status":"retrieved","request_started_at_jst":started.isoformat(),
                                   "fetch_elapsed_ms":elapsed_ms,
                                   "received_at_jst":received.isoformat(),"saved":len(written),
                                   "race_codes":written[:5],"source_rows":len(rows),
                                   "pre_deadline_2min":gate,"pre_deadline_12min":early,
                                   "late_reasons_2min":late_reasons,"late_examples_2min":late_samples,
                                   "six_lane_validation":six_lanes}
        except (HTTPError,URLError,TimeoutError,OSError,ValueError,UnicodeError,FileExistsError) as err:
            # A missing upstream daily CSV is different from invalid rows or a transport failure.
            # Never log full response bodies, credentials, or make a failed read look successful.
            reason=("upstream_http" if isinstance(err,HTTPError) else
                    "upstream_transport" if isinstance(err,(URLError,TimeoutError)) else
                    "local_or_invalid_source")
            checked_at=now()
            interpretation=("before_expected_publication_window" if isinstance(err,HTTPError) and err.code==404 and checked_at.hour<8 else
                            "not_published_or_missing" if isinstance(err,HTTPError) and err.code==404 else
                            "upstream_failure_or_invalid")
            status="source_unavailable" if reason in ("upstream_http","upstream_transport") else "capture_invalid"
            report["kinds"][kind]={"status":status,"error":type(err).__name__,"reason":reason,
                                   "availability_interpretation":interpretation,
                                   "http_status":err.code if isinstance(err,HTTPError) else None,
                                   "request_started_at_jst":started.isoformat(),
                                   "fetch_elapsed_ms":max(0,round((checked_at-started).total_seconds()*1000)),
                                   "received_at_jst":checked_at.isoformat(),"saved":0,
                                   "source_rows":None,"pre_deadline_2min":None,"pre_deadline_12min":None,
                                   "six_lane_validation":None}
    available=sum(1 for entry in report["kinds"].values() if entry.get("status") == "retrieved")
    report["sources_available"]=available
    report["sources_unavailable"]=sum(1 for entry in report["kinds"].values() if entry.get("status") == "source_unavailable")
    report["capture_invalid"]=sum(1 for entry in report["kinds"].values() if entry.get("status") == "capture_invalid")
    report["saved_total"]=sum(entry["saved"] for entry in report["kinds"].values())
    report["race_rows_total"]=sum(entry.get("source_rows") or 0 for entry in report["kinds"].values())
    # A successful Actions job must not be mistaken for successful upstream acquisition.
    before_window=(available == 0 and report["capture_invalid"] == 0 and all(entry.get("availability_interpretation")=="before_expected_publication_window" for entry in report["kinds"].values()))
    report["status"]=("not_yet_expected" if before_window else
                      "capture_invalid" if report["capture_invalid"] and available == 0 else
                      "source_unavailable" if available == 0 else
                      "partial_source_failure" if available < len(KINDS) and report["capture_invalid"] == 0 else
                      "partial_capture_failure" if available < len(KINDS) else
                      "sources_retrieved_no_rows" if report["race_rows_total"] == 0 else
                      "sources_retrieved")
    # Retain PR #654's independent per-race STT/TKZ paired coverage, without
    # treating a successfully fetched CSV as proof of preforecast availability.
    report["paired_six_lane_coverage"]=paired_six_lane_coverage(day,root)
    return report

if __name__=="__main__":
    report=collect()
    output=Path("late_preview_capture_report.json")
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(output.read_text(encoding="utf-8"))
