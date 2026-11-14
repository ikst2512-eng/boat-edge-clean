"""Research-only predeclared hole pair policies from 2026-11-06 onward.

NO production impact. Does not certify first remote receipt or formal accuracy.
Selector candidates are frozen and checked before a confirmed result is opened.
The precommitted selector modules remain byte-for-byte pinned in
hole_future_locked_eval.LOCKED_SELECTION_BLOBS; never rewrite historical picks.
"""
import argparse
import hashlib
import json
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from four_mode_archive_api import archived_four_modes, valid_ticket
from four_mode_frozen_diagnostic import compare_race
from hole_future_locked_eval import verify_locked_selection
from hole_pair_third_bundle_research import bundle
from hole_pair_diversification_research import diversify

JST=timezone(timedelta(hours=9))
FIRST_ELIGIBLE_DAY=date(2026,11,6)
METHOD="HOLE_PAIR_NOV06_LOCKED_RESEARCH_V1"
POLICIES=("baseline","same_pair_two_thirds","two_pairs_one_third")
TOPS=(1,3,5,10)
CODE=re.compile(r"20[0-9]{10}\Z")


def pair(ticket):
    return tuple(ticket.split("-")[:2])


def select(archive):
    modes=archive["modes"]
    base=[row["combo"] for row in modes["hole"]["tickets"][:10]]
    if len(base)!=10 or len(set(base))!=10 or any(not valid_ticket(t) for t in base):
        raise ValueError("invalid_original_top10")
    donors=list(dict.fromkeys(t["combo"] for m in ("hit","balance")
                               for t in modes[m]["tickets"]))
    proposals={
        "baseline":base,
        "same_pair_two_thirds":bundle(base,donors,rank=6,width=2),
        "two_pairs_one_third":diversify(archive),
    }
    pairs={pair(t) for t in base}
    for name,tickets in proposals.items():
        if (len(tickets)!=10 or len(set(tickets))!=10
                or any(not valid_ticket(t) for t in tickets)
                or tickets[:5]!=base[:5]
                or not pairs.issubset({pair(t) for t in tickets})):
            raise ValueError("candidate_contract_violation:"+name)
    return proposals


def top10_loss_diagnostic(original, proposed, winner):
    """Post-result attribution only; never used to select frozen tickets."""
    if winner not in original or winner in proposed:
        return None
    survivor = pair(winner) in {pair(ticket) for ticket in proposed}
    return {
        "original_rank": original.index(winner) + 1,
        "lost_ticket": winner,
        "first_second_pair_still_covered": survivor,
        "cause": ("third_choice_removed_despite_pair_coverage" if survivor
                  else "winning_first_second_pair_removed"),
        "removed_tickets": [ticket for ticket in original if ticket not in proposed],
        "added_tickets": [ticket for ticket in proposed if ticket not in original],
    }


def canonical_digest(data):
    return hashlib.sha256(json.dumps(
        data,ensure_ascii=False,sort_keys=True,separators=(",",":")
    ).encode("utf-8")).hexdigest()


def eligible(code):
    if type(code) is not str or not CODE.fullmatch(code):
        return False
    try: return date(int(code[:4]),int(code[4:6]),int(code[6:8]))>=FIRST_ELIGIBLE_DAY
    except ValueError: return False


def freeze(code,root,started_at=None,completed_at=None):
    """Freeze pre-cutoff; never read confirmed_results during this function."""
    root=Path(root)
    if not eligible(code):
        return {"race_code":code,"status":"not_yet_eligible_or_invalid_code",
                "formal":False,"production_forecast_changed":False}
    status,archive=archived_four_modes(code,root)
    if status!=200:
        return {"race_code":code,"status":"archive_unavailable_or_invalid",
                "formal":False,"production_forecast_changed":False}
    deadline=datetime.fromisoformat(archive["deadline_jst"])
    if deadline.utcoffset()!=timedelta(hours=9) or deadline.date()!=date(
        int(code[:4]),int(code[4:6]),int(code[6:8])):
        return {"race_code":code,"status":"invalid_deadline",
                "formal":False,"production_forecast_changed":False}
    cutoff=deadline-timedelta(minutes=12)
    started_at=started_at or datetime.now(timezone.utc)
    if not isinstance(started_at,datetime) or started_at.utcoffset() is None:
        raise ValueError("invalid_start_clock")
    if started_at>=cutoff:
        return {"race_code":code,"status":"after_t_minus_12",
                "formal":False,"production_forecast_changed":False}
    # An apparent freeze cannot precede the creation of its exact source forecast.
    # These local clocks are only fail-closed checks, NOT independent receipt proof.
    try:
        source_generated=datetime.fromisoformat(archive["generated_at_jst"])
        valid_source_clock=(source_generated.utcoffset()==timedelta(hours=9)
                            and source_generated<started_at and source_generated<cutoff)
    except (KeyError,TypeError,ValueError,AttributeError):
        valid_source_clock=False
    if not valid_source_clock:
        return {"race_code":code,"status":"source_not_generated_before_freeze",
                "formal":False,"production_forecast_changed":False}
    path=root/"four_mode_forecasts"/(code+".json")
    if path.is_symlink() or not path.is_file() or path.stat().st_size>30000:
        raise ValueError("unsafe_source_file")
    source_bytes=path.read_bytes()
    # Pin selector Git blobs, not merely semantic function names.
    locked=verify_locked_selection(root)
    method_source=Path(__file__).resolve()
    if method_source.is_symlink() or not method_source.is_file():
        raise ValueError("unsafe_method_source")
    method_sha256=hashlib.sha256(method_source.read_bytes()).hexdigest()
    choices=select(archive)
    completed_at=completed_at or datetime.now(timezone.utc)
    if not isinstance(completed_at,datetime) or completed_at.utcoffset() is None:
        raise ValueError("invalid_finish_clock")
    if completed_at<started_at:
        raise ValueError("clock_reversed")
    if completed_at>=cutoff:
        return {"race_code":code,"status":"calculation_crossed_t_minus_12",
                "formal":False,"production_forecast_changed":False}
    return {
        "schema":"HOLE_PAIR_FUTURE_FREEZE_V1","method":METHOD,
        "status":"locally_frozen_unverified","race_code":code,
        "model_version":archive["model_version"],
        "deadline_jst":archive["deadline_jst"],
        "t_minus_12_jst":cutoff.isoformat(),
        "local_start_jst":started_at.astimezone(JST).isoformat(),
        "local_finish_jst":completed_at.astimezone(JST).isoformat(),
        "source_sha256":hashlib.sha256(source_bytes).hexdigest(),
        "locked_selector_git_blobs":locked,
        "method_source_sha256":method_sha256,
        "candidates":choices,
        "candidates_sha256":canonical_digest(choices),
        "formal":False,"prospective_validation":False,
        "independent_first_receipt_verified":False,
        "production_forecast_changed":False,
        "warning":"Candidate frozen by a local clock only. No independently verified first receipt; cannot report formal accuracy.",
    }


def review(record,root):
    """Replay candidates from archive before fetching result; always NONFORMAL."""
    root=Path(root)
    if not isinstance(record,dict) or record.get("status")!="locally_frozen_unverified":
        return {"status":"no_eligible_frozen_candidate","comparable":0,"formal":False}
    code=record.get("race_code")
    if (not eligible(code) or record.get("schema")!="HOLE_PAIR_FUTURE_FREEZE_V1"
            or record.get("method")!=METHOD or
            record.get("independent_first_receipt_verified") is not False or
            record.get("formal") is not False or
            record.get("prospective_validation") is not False or
            record.get("production_forecast_changed") is not False):
        return {"status":"invalid_method_or_claim","comparable":0,"formal":False}
    state,archive=archived_four_modes(code,root)
    if state!=200:return {"status":"archive_invalid","comparable":0,"formal":False}
    path=root/"four_mode_forecasts"/(code+".json")
    if (path.is_symlink() or not path.is_file() or path.stat().st_size>30000
            or hashlib.sha256(path.read_bytes()).hexdigest()!=record.get("source_sha256")):
        return {"status":"source_mismatch","comparable":0,"formal":False}
    try:
        start=datetime.fromisoformat(record["local_start_jst"])
        finish=datetime.fromisoformat(record["local_finish_jst"])
        deadline=datetime.fromisoformat(archive["deadline_jst"])
        generated=datetime.fromisoformat(archive["generated_at_jst"])
        cutoff=deadline-timedelta(minutes=12)
        if (generated.utcoffset()!=timedelta(hours=9) or
                generated>=start or generated>=cutoff or
                start.utcoffset()!=timedelta(hours=9) or
                finish.utcoffset()!=timedelta(hours=9) or
                deadline.utcoffset()!=timedelta(hours=9) or
                start>finish or finish>=cutoff or
                record.get("t_minus_12_jst")!=cutoff.isoformat() or
                record.get("deadline_jst")!=archive["deadline_jst"] or
                record.get("model_version")!=archive["model_version"]):
            raise ValueError("clock_or_archive_mismatch")
    except (ValueError,KeyError,TypeError):
        return {"status":"timing_mismatch","comparable":0,"formal":False}
    locked=verify_locked_selection(root)
    method_source=Path(__file__).resolve()
    if (method_source.is_symlink() or not method_source.is_file() or
            hashlib.sha256(method_source.read_bytes()).hexdigest()!=record.get("method_source_sha256")):
        return {"status":"method_source_changed","comparable":0,"formal":False}
    if record.get("locked_selector_git_blobs")!=locked:
        return {"status":"selector_changed","comparable":0,"formal":False}
    # Replay BEFORE opening settled result; a wrong ticket is not scored.
    choices=select(archive)
    if (record.get("candidates")!=choices or
            record.get("candidates_sha256")!=canonical_digest(choices)):
        return {"status":"candidate_replay_mismatch","comparable":0,"formal":False}
    outcome=compare_race(code,root)
    if outcome.get("status")!="historical_comparison_only":
        return {"status":"result_not_yet_confirmed","comparable":0,"formal":False}
    winner=outcome["winning_ticket"]
    rank={name:(picks.index(winner)+1 if winner in picks else 0)
          for name,picks in choices.items()}
    flags={name:{f"top{k}":bool(rank[name]) and rank[name]<=k for k in TOPS}
           for name in POLICIES}
    gains={}
    for name in POLICIES[1:]:
        gains[name]={
            f"top{k}":{
                "gained":int(flags[name][f"top{k}"] and not flags["baseline"][f"top{k}"]),
                "lost":int(flags["baseline"][f"top{k}"] and not flags[name][f"top{k}"]),
            } for k in TOPS
        }
    if any(gains[name][f"top{k}"]["gained"] or
           gains[name][f"top{k}"]["lost"] for name in POLICIES[1:] for k in (1,3,5)):
        raise ValueError("protected_top5_changed")
    # Explain losses only AFTER winner has been independently read and candidates replayed.
    top10_losses = {
        name: top10_loss_diagnostic(choices["baseline"], choices[name], winner)
        for name in POLICIES[1:]
    }
    if any(int(top10_losses[name] is not None) != gains[name]["top10"]["lost"]
           for name in POLICIES[1:]):
        raise ValueError("top10_loss_diagnostic_mismatch")
    return {
        "status":"reference_scored_without_independent_receipt",
        "race_code":code,"comparable":1,"ranks":rank,"flags":flags,"gain_loss":gains,
        "top10_loss_diagnostics":top10_losses,
        "formal":False,"prospective_validation":False,
        "independent_first_receipt_verified":False,
        "production_forecast_changed":False,
        "warning":"Result is confirmed, but local freeze time and git timestamps alone never establish independent pre-cutoff receipt.",
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("race_code")
    p.add_argument("--root",default=".")
    p.add_argument("--output",default="")
    args=p.parse_args()
    result=freeze(args.race_code,args.root)
    if args.output:
        output=Path(args.output)
        output.parent.mkdir(parents=True,exist_ok=True)
        if output.exists():raise ValueError("immutable_freeze_output_already_exists")
        with output.open("x",encoding="utf-8") as fd:
            json.dump(result,fd,ensure_ascii=False,sort_keys=True,indent=2)
            fd.write("\n")
    print(json.dumps({k:v for k,v in result.items() if k not in ("candidates","locked_selector_git_blobs")},
                     ensure_ascii=False,sort_keys=True))

if __name__=="__main__":main()
