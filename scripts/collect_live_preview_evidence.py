"""Fetch live preview CSV and archive only observations made before race deadline.

Output belongs exclusively to an Actions artifact, not research_snapshots or
published predictions. Safe to run even when no eligible races exist.
"""
import json, sys, tempfile
from datetime import datetime, timedelta
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError,URLError
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from research_model import JST
from late_preview_capture import save_preview, KINDS, six_lane_status
from scripts.preview_timing_integrity import classify
from scripts.research_preview_csv_probe import BASE

def paired_six_lane_coverage(day, root):
    """Count only races with independently saved complete tkz and stt evidence."""
    sets = {}
    early_sets = {}
    for kind in ("tkz", "stt"):
        good = set()
        early = set()
        for file in (Path(root) / day / kind).glob("*.json"):
            try:
                record = json.loads(file.read_text(encoding="utf-8"))
                if (record.get("race_code") == file.stem and record.get("kind") == kind
                        and isinstance(record.get("source_row"), dict)
                        and record["source_row"].get("レースコード") == file.stem
                        and record.get("six_lane_validation") == "complete"
                        and six_lane_status(kind, record["source_row"]) == "complete"
                        and record.get("status") == "late_preview_unvalidated_not_research_forecast"
                        and record.get("source_observed_jst") == record["source_row"].get("取得日時")
                        and datetime.fromisoformat(record["received_at_jst"]).utcoffset() is not None
                        and classify(record["source_row"], datetime.fromisoformat(record["received_at_jst"]), margin_minutes=0) == "pre_cutoff_observed"
                        and datetime.fromisoformat(record["received_at_jst"]) <
                            datetime.strptime(file.stem[:8] + record["source_row"]["締切時刻"], "%Y%m%d%H:%M").replace(tzinfo=JST) - timedelta(minutes=2)):
                    good.add(file.stem)
                    # Retrospective 12-minute timing audit only: never feed forecasts.
                    if classify(record["source_row"], datetime.fromisoformat(record["received_at_jst"]), margin_minutes=12) == "pre_cutoff_observed":
                        early.add(file.stem)
            except (OSError, ValueError, TypeError, AttributeError):
                continue
        sets[kind] = good
        early_sets[kind] = early
    return {"tkz_complete": len(sets["tkz"]), "stt_complete": len(sets["stt"]),
            "paired_complete": len(sets["tkz"] & sets["stt"]),
            "paired_codes": sorted(sets["tkz"] & sets["stt"]),
            "paired_12min_observable": len(early_sets["tkz"] & early_sets["stt"]),
            "paired_12min_codes": sorted(early_sets["tkz"] & early_sets["stt"]),
            "timing_audit_scope": "retrospective_only_not_forecast_input"}


def collect(day, root, fetch=None):
    datetime.strptime(day,"%Y%m%d")
    summary={"day":day,"capture_policy":"before_deadline_minus_2min_buffer",
             "source_expected_window_jst":"08:00-22:59",
             "source_snapshot_policy":"nominal_cutoff_minus_5min_not_formal_T12",
             "kinds":{}}
    for kind in KINDS:
        url=f"{BASE}{kind}/{day[:4]}/{day[4:6]}/{day[6:]}.csv"
        try:
            if fetch is None:
                with urlopen(Request(url,headers={"User-Agent":"BOAT-EDGE-CLEAN-RESEARCH/1.0"}),timeout=8) as response:
                    raw=response.read(3_000_001)
                    received=datetime.now(JST)
            else:
                raw,received=fetch(url)
            records=save_preview(raw,kind,day,received,root)
            states=[json.loads((Path(root)/day/kind/(code+".json")).read_text(encoding="utf-8")).get("six_lane_validation") for code in records]
            summary["kinds"][kind]={"status":"ok","saved":len(records),
                                    "six_lane_complete":states.count("complete"),
                                    "six_lane_incomplete":states.count("incomplete")}
        except (HTTPError,URLError,TimeoutError,OSError,ValueError,UnicodeError,FileExistsError) as error:
            summary["kinds"][kind]={"status":"unavailable_or_invalid","error":type(error).__name__}
            if isinstance(error, HTTPError):
                summary["kinds"][kind]["http_status"]=error.code
                summary["kinds"][kind]["checked_at_jst"]=datetime.now(JST).isoformat()
                checked=datetime.now(JST)
                summary["kinds"][kind]["availability_interpretation"]=("before_upstream_schedule_or_missing" if checked.hour<8 and error.code==404 else "not_published_or_missing" if error.code==404 else "http_failure")
    summary["paired_six_lane_coverage"]=paired_six_lane_coverage(day,root)
    return summary

def write_summary(day, root, summary):
    """Persist an inspectable audit result with the evidence; never publish forecasts."""
    if summary.get("day") != day:
        raise ValueError("summary day mismatch")
    target=Path(root)/day/"collection_summary.json"
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return target

if __name__=="__main__":
    day=datetime.now(JST).strftime("%Y%m%d")
    root=Path("late_preview_evidence")
    summary=collect(day,root)
    write_summary(day,root,summary)
    print(json.dumps(summary,ensure_ascii=False))
