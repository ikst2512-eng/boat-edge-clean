"""Manual research prospective freeze; never modifies existing forecast or formal Fresh.

Run only after daily saved research snapshots exist and strictly before each
snapshot's cutoff. Output files must be committed/published before cutoff for
meaningful prospective evidence. No automatic scheduling or promotion.
"""
import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

from research_model import JST, probabilities
from research_scenario_candidate import scenario_probabilities

CANDIDATE_BLOB_SHA = "724cf7e83d491f4570bdd28cec72720cf5d03815"
BASELINE_MODEL_ID = "national-beta0.4-exploratory-v1"
CANDIDATE_MODEL_ID = "scenario-exploratory-20261027-unvalidated"

def freeze_record(snapshot, now):
    if snapshot.get("status") != "research" or snapshot.get("validated") is not False:
        raise ValueError("not research snapshot")
    if snapshot.get("model_version") != BASELINE_MODEL_ID:
        raise ValueError("unexpected baseline version")
    cutoff = datetime.fromisoformat(snapshot["cutoff_jst"])
    generated = datetime.fromisoformat(snapshot["generated_at"])
    received = [datetime.fromisoformat(snapshot[k]) for k in ("source_title_received_jst","source_cards_received_jst")]
    if any(x.tzinfo is None or x.utcoffset() is None for x in [cutoff, generated, now, *received]):
        raise ValueError("naive timestamp")
    if max(generated, *received, now) >= cutoff:
        raise ValueError("not safely before cutoff")
    rates = snapshot["national_win_rates"]
    baseline = {"-".join(map(str, t)): p for t,p in probabilities(rates)}
    ranked = ["-".join(map(str,t)) for t,p in probabilities(rates)[:10]]
    if ranked != snapshot["predictions"]:
        raise ValueError("baseline replay mismatch")
    # No actual-entry evidence is present; default-entry scenario is an
    # explicit assumption, not a fact discovered from result data.
    candidate = {"-".join(map(str,t)): p for t,p in scenario_probabilities(rates)}
    return {"race_code": snapshot["race_code"], "status":"research_unvalidated",
            "cutoff_jst": cutoff.isoformat(), "frozen_at_jst": now.isoformat(),
            "source_snapshot_generated_at": generated.isoformat(),
            "candidate_model_id": CANDIDATE_MODEL_ID, "candidate_git_blob_sha": CANDIDATE_BLOB_SHA,
            "baseline_model_id":BASELINE_MODEL_ID,
            "entry_status":"assumed_identity_not_verified", "features_used":["national_win_rates"],
            "baseline":baseline,"candidate":candidate,
            "source_snapshot_sha256":hashlib.sha256(json.dumps(snapshot,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest(),
            "prospective_verified":False}

def capture(day, source_dir, output_dir, now=None):
    if len(day) != 8 or not day.isascii() or not day.isdigit():
        raise ValueError("invalid day")
    now = now or datetime.now(JST)
    source, target = Path(source_dir), Path(output_dir)
    if not source.is_dir():
        raise ValueError("snapshot directory unavailable")
    target.mkdir(parents=True, exist_ok=True)
    counts = {"frozen":0,"already_frozen":0,"ineligible":0}
    for src in sorted(source.glob(day+"*.json")):
        record = json.loads(src.read_text(encoding="utf-8"))
        if src.stem != record.get("race_code"):
            raise ValueError("snapshot path mismatch")
        dst = target / src.name
        if dst.exists():
            counts["already_frozen"] += 1
            continue
        try:
            frozen=freeze_record(record,now)
        except (ValueError,TypeError,KeyError):
            counts["ineligible"] += 1
            continue
        with dst.open("x",encoding="utf-8") as handle:
            json.dump(frozen,handle,ensure_ascii=False,sort_keys=True,separators=(",",":"))
            handle.flush()
            import os
            os.fsync(handle.fileno())
        counts["frozen"] += 1
    return counts

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--day",default=datetime.now(JST).strftime("%Y%m%d"))
    p.add_argument("--snapshots",default="research_snapshots")
    p.add_argument("--output",default="research_prospective_pairs")
    args=p.parse_args()
    print(json.dumps(capture(args.day,args.snapshots,args.output),ensure_ascii=False))
