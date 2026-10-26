"""Opt-in research publishing pipeline, never scheduled or used by production.

Sequence: existing baseline collection -> paired freeze -> safe Git commit ->
optional remote push. No result data is used as forecast input.
"""
import argparse
import json
from datetime import datetime
from research_model import JST
from research_collect_and_pair import run as collect_and_pair
from research_pair_git_prepare import prepare
from research_pair_remote_publish import push

def run(day, publish=False, commit=False):
    # Never replay an earlier/future date as if freshly frozen.
    today=datetime.now(JST).strftime("%Y%m%d")
    if day != today:
        raise ValueError("research prospective pipeline requires current JST date")
    if publish and not commit:
        raise ValueError('remote push requires explicit commit opt-in')
    collected=collect_and_pair(day)
    if collected["paired"]["frozen"] == 0 and collected["paired"]["already_frozen"] == 0:
        return {"collection":collected,"publication":"skipped_no_pairs",
                "prospective_verified":False}
    if not commit:
        return {'collection':collected,'publication':'not_requested',
                'prospective_verified':False}
    committed=prepare(day)
    publication=push(day,dry_run=not publish)
    return {"collection":collected,"commit":committed,"publication":publication,
            "prospective_verified":False}

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--day",default=datetime.now(JST).strftime("%Y%m%d"))
    p.add_argument("--push",action="store_true")
    p.add_argument("--commit",action="store_true")
    a=p.parse_args()
    print(json.dumps(run(a.day,a.push,a.commit),ensure_ascii=False))
