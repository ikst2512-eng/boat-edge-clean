"""Verify a pre-deadline receipt before extracting exactly six exhibition times.

Offline only: reads local receipt/source.html and receipt/metadata.json.
Does not read results, compute probabilities, or attest runner clock independently.
"""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit, parse_qs
from exhibition_parser import extract

def verify(folder: Path, cutoff_jst: str):
    meta = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    body = (folder / "source.html").read_bytes()
    cutoff = dt.datetime.fromisoformat(cutoff_jst)
    if cutoff.utcoffset() != dt.timedelta(hours=9):
        raise ValueError("cutoff must specify +09:00")
    race_id = meta["race_id"]
    if cutoff.strftime("%Y%m%d") != race_id[:8]:
        raise ValueError("cutoff date mismatches race")
    if hashlib.sha256(body).hexdigest() != meta["source_sha256"] or len(body) != meta["source_bytes"]:
        raise ValueError("source hash or byte count mismatch")
    if meta.get("http_status") != 200 or "html" not in meta.get("content_type","").lower():
        raise ValueError("invalid source response")
    url = urlsplit(meta["url"])
    q = parse_qs(url.query)
    if url.scheme != "https" or url.hostname != "www.boatrace.jp" or url.path != "/owpc/pc/race/beforeinfo":
        raise ValueError("unapproved source")
    if q.get("hd") != [race_id[:8]] or q.get("jcd") not in ([race_id[8:10]], [str(int(race_id[8:10]))]) or q.get("rno") != [str(int(race_id[10:12]))]:
        raise ValueError("race identity differs from source URL")
    started = dt.datetime.fromisoformat(meta["utc_start"])
    ended = dt.datetime.fromisoformat(meta["utc_end"])
    if started.tzinfo is None or ended.tzinfo is None or started > ended:
        raise ValueError("invalid receipt times")
    remaining_start = (cutoff - started).total_seconds()
    remaining_end = (cutoff - ended).total_seconds()
    if not (720 < remaining_end <= remaining_start <= 1200):
        raise ValueError("receipt outside 20–12m cutoff window")
    if meta.get("clock_attestation") != "runner_local_only" or meta.get("scoring") != "NOT_RUN":
        raise ValueError("receipt provenance invalid")
    # No independently certified result-free attestation is available yet.
    # Refuse the numeric extraction instead of turning a token scan into an attestation.
    raise ValueError("RESULT_FREE_ATTESTATION_MISSING: numeric extraction remains LOCKED")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--receipt-dir",required=True,type=Path)
    ap.add_argument("--cutoff-jst",required=True)
    args = ap.parse_args()
    try:
        verify(args.receipt_dir,args.cutoff_jst)
    except (ValueError,KeyError,FileNotFoundError,json.JSONDecodeError) as ex:
        print(json.dumps({"status":"REJECTED","reason":str(ex),"scoring":"NOT_RUN","unlock":"LOCKED"},ensure_ascii=False))
        raise SystemExit(2)
    raise AssertionError("unreachable")

if __name__=="__main__":
    main()
