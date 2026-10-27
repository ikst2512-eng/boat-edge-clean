"""Independent pre-cutoff prospective prediction capture.

This is *not* a validated formal forecast: publication, remote Git first-add
attestation and out-of-sample accuracy promotion are separate gates.
Never uses old boat-edge or post-result snapshots.
"""
import argparse
import hashlib
import json
import os
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from research_model import JST, BASE, read_rows, probabilities, model_provenance

ROOT = Path(__file__).resolve().parent
STORE = ROOT / "prospective_predictions"
VERSION = "clean-prospective-national-beta0.4-v1"

def build(day, titles, cards, title_received, cards_received, title_digest, card_digest, now, provenance):
    counts = Counter(r.get("レースコード") for r in titles if isinstance(r, dict))
    card_counts = Counter(r.get("レースコード") for r in cards if isinstance(r, dict))
    by_card = {r["レースコード"]: r for r in cards if isinstance(r, dict) and card_counts[r.get("レースコード")] == 1 and r.get("レースコード")}
    items = {}
    for row in titles:
        code = row.get("レースコード") if isinstance(row, dict) else None
        if not isinstance(code, str) or len(code) != 12 or not code.isascii() or not code.isdigit() or not code.startswith(day):
            continue
        if counts[code] != 1 or card_counts[code] != 1 or code not in by_card:
            continue
        try:
            deadline = datetime.strptime(day + row["電話投票締切予定"], "%Y%m%d%H:%M").replace(tzinfo=JST)
            cutoff = deadline - timedelta(minutes=12)
            if max(now, title_received, cards_received) >= cutoff:
                continue
            rates = [float(by_card[code][f"艇{i}_全国勝率"]) for i in range(1,7)]
            outcomes = probabilities(rates)
            tickets = ["-".join(map(str, p)) for p, _ in outcomes[:10]]
            items[code] = {
                "race_code":code, "status":"prospective_candidate",
                "formal":False, "validated":False, "scoring":False,
                "predictions":tickets, "model_version":VERSION,
                "generated_at":now.isoformat(), "source_deadline_jst":deadline.isoformat(),
                "cutoff_jst":cutoff.isoformat(), "source_title_received_jst":title_received.isoformat(),
                "source_cards_received_jst":cards_received.isoformat(),
                "source_title_sha256":title_digest, "source_cards_sha256":card_digest,
                "input_sha256":hashlib.sha256((title_digest+":"+card_digest).encode()).hexdigest(),
                "national_win_rates":rates, **provenance,
                "attestation":"pending Git remote first-add verification",
            }
        except (ValueError, KeyError, TypeError, OverflowError):
            continue
    return items

def collect(day=None):
    now = datetime.now(JST)
    day = day or now.strftime("%Y%m%d")
    datetime.strptime(day, "%Y%m%d")
    path=f"{day[:4]}/{day[4:6]}/{day[6:]}.csv"
    titles,t1,h1=read_rows(BASE+"title/"+path)
    cards,t2,h2=read_rows(BASE+"race_cards/"+path)
    provenance=model_provenance()
    output=build(day,titles,cards,t1,t2,h1,h2,now,provenance)
    saved=0
    for code,record in sorted(output.items()):
        STORE.mkdir(exist_ok=True)
        target=STORE/(code+".json")
        if target.is_symlink():
            raise ValueError("symlink candidate prohibited")
        try:
            with target.open("x",encoding="utf-8") as f:
                json.dump(record,f,ensure_ascii=False,sort_keys=True)
                f.flush()
                os.fsync(f.fileno())
            saved+=1
        except FileExistsError:
            if json.loads(target.read_text(encoding="utf-8")).get("race_code")!=code:
                raise ValueError("existing candidate conflict")
    return {"date":day,"saved":saved,"eligible":len(output),
            "formal_predictions":0,"scoring_enabled":False}

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--date")
    print(json.dumps(collect(p.parse_args().date),ensure_ascii=False))
