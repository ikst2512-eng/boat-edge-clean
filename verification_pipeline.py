"""CLEAN V236 prediction/result verification stages. No post-result prediction creation.

Runs on CLEAN-owned immutable v236_forecasts and confirmed_results. Writes
atomic status reports with explicit actionable blockers; unfinished races are
revisited on the next run. Never counts absent predictions as misses or hits.
"""
from __future__ import annotations
import argparse
import csv
import io
import json
import os
import re
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent
RE_RACE = re.compile(r"^\d{8}(?:0[1-9]|1\d|2[0-4])(?:0[1-9]|1[0-2])$")
RE_TICKET = re.compile(r"^[1-6]-[1-6]-[1-6]$")
PAYOUT_BASE = "https://boatracecsv.github.io/data/results/payouts"
STATES = {"waiting_prediction", "waiting_result", "waiting_payout", "complete", "invalid_record"}


def valid_ticket(value):
    return isinstance(value, str) and RE_TICKET.fullmatch(value) is not None and len(set(value.split("-"))) == 3


def stake_for_rank(rank):
    # 5000 yen / 15 bets, 100-yen increments; first five get 400 yen.
    return 400 if rank < 5 else 300


def read_json(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 30000:
        raise ValueError("archive_missing_or_invalid")
    return json.loads(path.read_text(encoding="utf-8"))


def validate_forecast(data, race):
    if data.get("race_code") != race or data.get("model") != "V236_coverage15":
        raise ValueError("forecast_identity")
    picks = data.get("tickets")
    if not isinstance(picks, list) or len(picks) != 15 or len(set(picks)) != 15 or not all(valid_ticket(p) for p in picks):
        raise ValueError("forecast_tickets")
    cutoff, saved = data.get("deadline_jst"), data.get("saved_at_jst")
    if not isinstance(cutoff, str) or not isinstance(saved, str):
        raise ValueError("freeze_missing")
    deadline = datetime.fromisoformat(cutoff)
    frozen = datetime.fromisoformat(saved)
    if deadline.utcoffset() is None or frozen.utcoffset() is None or frozen >= deadline:
        raise ValueError("not_frozen_before_deadline")
    if sum(stake_for_rank(i) for i in range(15)) != 5000:
        raise ValueError("budget")
    return picks


def attest_first_git_add(path, deadline):
    """Require first Git add of exact unchanged bytes before scheduled deadline."""
    base = ROOT
    relative = str(path.relative_to(base))
    def git(*args):
        return subprocess.check_output(["git", "-C", str(base), *args], stderr=subprocess.DEVNULL, timeout=12)
    commits = git("log", "--reverse", "--diff-filter=A", "--format=%H", "--", relative).decode().splitlines()
    if len(commits) != 1:
        raise ValueError("no_unique_first_add")
    sha = commits[0]
    original = git("show", sha + ":" + relative)
    if original != path.read_bytes():
        raise ValueError("archive_mutated")
    first_commit = git("show", "-s", "--format=%cI", sha).decode().strip()
    recorded = datetime.fromisoformat(first_commit)
    if recorded >= datetime.fromisoformat(deadline):
        raise ValueError("first_add_after_deadline")
    return sha


def validate_result(data, race):
    order = data.get("finish_order")
    if data.get("race_code") != race or data.get("status") != "confirmed":
        raise ValueError("result_identity")
    if not isinstance(order, list) or len(order) != 3 or any(not isinstance(v, int) or isinstance(v, bool) or v not in range(1, 7) for v in order) or len(set(order)) != 3:
        raise ValueError("result_finish")
    if not str(data.get("source_url", "")).startswith("https://") or not data.get("confirmed_at_jst"):
        raise ValueError("result_proof")
    return "-".join(map(str, order))


def payout_for(race, ticket, download=urlopen):
    y, m, d = race[:4], race[4:6], race[6:8]
    url = f"{PAYOUT_BASE}/{y}/{m}/{d}.csv"
    with download(url, timeout=12) as res:
        blob = res.read(2000001)
    if len(blob) > 2000000:
        raise ValueError("payout_too_large")
    reader = csv.DictReader(io.StringIO(blob.decode("utf-8-sig")))
    fields = reader.fieldnames or []
    if not all(n in fields for n in ("レースコード", "3連単_組番", "3連単_払戻金")):
        raise ValueError("payout_schema")
    rows = [row for row in reader if row.get("レースコード") == race]
    if len(rows) != 1 or rows[0].get("3連単_組番") != ticket:
        raise ValueError("payout_mismatch")
    number = rows[0]["3連単_払戻金"].replace(",", "").replace("円", "").strip()
    if not number.isdecimal() or not 100 <= int(number) <= 99999999:
        raise ValueError("payout_invalid")
    return int(number)


def diagnose(picks, result):
    rank = picks.index(result) if result in picks else -1
    if rank >= 0:
        return "hit", rank
    first, second, _ = result.split("-")
    if not any(p.split("-")[0] == first for p in picks):
        return "first_missing", -1
    if not any(p.startswith(first + "-" + second + "-") for p in picks):
        return "second_missing", -1
    return "third_missing", -1


def evaluate(race, root=ROOT, payout_loader=payout_for, proof_checker=attest_first_git_add):
    report = {"race_code": race, "model": "V236_coverage15", "budget_yen": 5000}
    if not RE_RACE.fullmatch(race):
        return {**report, "state": "invalid_record", "reason": "race_code"}
    pred_file = root / "v236_forecasts" / (race + ".json")
    res_file = root / "confirmed_results" / (race + ".json")
    if not pred_file.is_file():
        return {**report, "state": "waiting_prediction", "reason": "forecast_not_frozen"}
    try:
        frozen = read_json(pred_file)
        picks = validate_forecast(frozen, race)
        proof_checker(pred_file, frozen['deadline_jst'])
    except (ValueError, TypeError, KeyError, OSError, subprocess.SubprocessError, TimeoutError) as err:
        return {**report, "state": "invalid_record", "reason": str(err), "stage": "prediction"}
    if not res_file.is_file():
        return {**report, "state": "waiting_result", "reason": "official_result_missing"}
    try:
        combo = validate_result(read_json(res_file), race)
    except (ValueError, TypeError, KeyError, OSError) as err:
        return {**report, "state": "invalid_record", "reason": str(err), "stage": "result"}
    reason, rank = diagnose(picks, combo)
    report.update({"result": combo, "hit": rank >= 0, "miss_reason": reason, "pick_rank": rank + 1 if rank >= 0 else None})
    try:
        payout = payout_loader(race, combo)
    except Exception as err:
        return {**report, "state": "waiting_payout", "reason": type(err).__name__}
    if not isinstance(payout, int) or payout < 100:
        return {**report, "state": "waiting_payout", "reason": "payout_invalid"}
    returned = payout * stake_for_rank(rank) // 100 if rank >= 0 else 0
    return {**report, "state": "complete", "payout_per_100_yen": payout, "return_yen": returned,
            "profit_yen": returned - 5000, "roi_pct": round(returned / 50, 2)}


def save_atomic(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix="._verification_", suffix=".json", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fp:
            json.dump(data, fp, ensure_ascii=False, indent=2, sort_keys=True)
            fp.write("\n")
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def run(root=ROOT):
    # Existing statuses are included so missing upstream data is retried;
    # confirmed results also seed races even when forecast is absent.
    ids = set()
    for directory in ("v236_forecasts", "confirmed_results", "verification_status"):
        path = root / directory
        if path.exists():
            ids.update(p.stem for p in path.glob("*.json") if RE_RACE.fullmatch(p.stem))
    records = []
    for race in sorted(ids):
        record = evaluate(race, root)
        save_atomic(root / "verification_status" / (race + ".json"), record)
        records.append(record)
    complete = [r for r in records if r["state"] == "complete"]
    hit = sum(r["hit"] for r in complete)
    invested = 5000 * len(complete)
    returned = sum(r["return_yen"] for r in complete)
    summary = {"model": "V236_coverage15", "eligible_complete_races": len(complete),
               "hit_races": hit, "hit_rate_pct": round(hit * 100 / len(complete), 2) if complete else None,
               "invested_yen": invested, "return_yen": returned, "profit_yen": returned - invested,
               "roi_pct": round(returned * 100 / invested, 2) if invested else None,
               "states": {s: sum(r["state"] == s for r in records) for s in sorted(STATES)}}
    save_atomic(root / "verification_status" / "summary.json", summary)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    print(json.dumps(run(args.root), ensure_ascii=False))
