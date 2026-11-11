"""Frozen research-only four-mode shadow from immutable published first-add originals.

Run in existing SAME capture job after GitHub original-blob observation, not later
from confirmed results. This file never writes existing forecasts or reads results.
A local pre-T12 freeze and observed ORIGINAL do NOT prove remote candidate receipt.
"""
import argparse
import hashlib
import json
import math
import re
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

from clean_four_modes import rank_modes
from research_model import probabilities

SCHEMA = "FOUR_MODE_ALL_SHADOW_AFTER_PUSH_RESEARCH_V1"
VERSION = "CLEAN_FOUR_MODES_V2_PROVISIONAL_UNCALIBRATED"
JST = timezone(timedelta(hours=9))
SIZES = {"narrow": 5, "hit": 10, "balance": 16, "hole": 22}
PROTECTED = {"narrow": 1, "hit": 3, "balance": 3, "hole": 5}
TOP1_PAIR_RULE = "pre_result_national_win_rates_lexicographic_head_second_third_v1"
POOLS = {"narrow": (0, 30), "hit": (0, 45),
         "balance": (0, 65), "hole": (10, 85)}
SHA40 = re.compile(r"[0-9a-f]{40}\Z")
SHA64 = re.compile(r"[0-9a-f]{64}\Z")
FORECAST_PATH = re.compile(r"four_mode_forecasts/(20[0-9]{10})\.json\Z")


def at_jst(x):
    try:
        value = datetime.fromisoformat(x) if isinstance(x, str) else x
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid_clock") from exc
    if not isinstance(value, datetime) or value.utcoffset() != timedelta(hours=9):
        raise ValueError("non_JST_clock")
    return value


def _tickets(record, mode):
    rows = record["modes"][mode]["tickets"]
    if type(rows) is not list or len(rows) != SIZES[mode]:
        raise ValueError("invalid_mode_ticket_count")
    tickets = [row["combo"] for row in rows]
    if len(set(tickets)) != len(tickets) or any(
        type(t) is not str or not re.fullmatch(r"[1-6]-[1-6]-[1-6]", t)
        or len(set(t.split("-"))) != 3 for t in tickets
    ):
        raise ValueError("invalid_original_tickets")
    return tickets


def candidate_modes(raw):
    """Deterministic, pre-result heuristic. Historical hit rates do not enter."""
    if (type(raw) is not dict or raw.get("schema") != "CLEAN_FOUR_MODES_PREDEADLINE_V1"
            or raw.get("model_version") != VERSION or raw.get("validated") is not False):
        raise ValueError("invalid_v2_original")
    if any(k in raw for k in ("finish_order", "winning_ticket", "confirmed_result", "result", "payout", "confirmed_at_jst")):
        raise ValueError("postrace_content_in_forecast")
    rates = raw.get("input_national_win_rates")
    if (type(rates) is not list or len(rates) != 6 or
            any(type(x) not in (float, int) or not math.isfinite(x)
                or x < 0 or x > 10 for x in rates)):
        raise ValueError("invalid_six_national_rates")
    board = probabilities(rates)
    expected = rank_modes(board)
    if (len(board) != 120 or len(set(combo for combo, _ in board)) != 120 or
            any([(t["combo"], t["p"]) for t in raw["modes"][m]["tickets"]]
                != [(t["combo"], t["p"]) for t in expected[m]["tickets"]]
                for m in SIZES)):
        raise ValueError("original_not_exactly_reproducible")
    ranked = sorted(
        [("-".join(map(str, combo)), float(prob)) for combo, prob in board],
        key=lambda item: (-item[1], item[0])
    )
    baseline = {mode: _tickets(raw, mode) for mode in SIZES}
    shadow = {}
    for mode, old in baseline.items():
        selected = list(old[:PROTECTED[mode]])
        lo, hi = POOLS[mode]
        pool = {combo: prob for combo, prob in ranked[lo:hi]}
        # Keep all original tickets available in case a mode contains an
        # unusual probability order or the medium-range hole set.
        pool.update({combo: prob for combo, prob in ranked if combo in old})
        for combo in selected:
            pool.pop(combo, None)
        while len(selected) < len(old):
            pairs = {x[:3] for x in selected}
            heads = {x[0] for x in selected}
            # One structural exploratory hypothesis; no fitting to Nov 5
            # finishing order. Never interpret these as recalibrated p values.
            choice = max(pool, key=lambda combo: (
                pool[combo] * (1.5 if combo[:3] not in pairs else 1.0)
                * (1.1 if combo[0] not in heads else 1.0),
                pool[combo], combo
            ))
            selected.append(choice)
            del pool[choice]
        if (len(selected) != SIZES[mode] or len(set(selected)) != SIZES[mode]
                or selected[:PROTECTED[mode]] != old[:PROTECTED[mode]]):
            raise ValueError("candidate_ticket_invariant")
        shadow[mode] = selected
    return baseline, shadow


def top1_pair_candidate(raw, baseline):
    """Separate Top1-only hypothesis: reorder the existing first two tickets.

    National win rates are available in the frozen forecast BEFORE the result.
    Compare the predicted boat strengths lexicographically by finishing place.
    This is NOT a calibrated probability estimate. All Top2/3/5/10 ticket
    MEMBERSHIPS remain exactly identical to the baseline, regardless of swaps.
    Call only after candidate_modes(raw) has validated the full original.
    """
    rates = raw["input_national_win_rates"]
    reordered = {}
    for mode in SIZES:
        old = baseline[mode]
        if len(old) != SIZES[mode] or len(set(old)) != len(old):
            raise ValueError("invalid_top1_baseline")
        chosen = list(old)
        def strength(combo):
            return tuple(rates[int(boat) - 1] for boat in combo.split("-"))
        if strength(chosen[1]) > strength(chosen[0]):
            chosen[0], chosen[1] = chosen[1], chosen[0]
        if (set(chosen[:2]) != set(old[:2]) or chosen[2:] != old[2:]
                or any(set(chosen[:n]) != set(old[:n]) for n in (3, 5, 10))):
            raise ValueError("top1_pair_preservation_failed")
        reordered[mode] = chosen
    return reordered


def _empty(status):
    return {"schema": SCHEMA, "status": status, "formal": False,
            "candidate_first_remote_receipt_verified": False,
            "production_forecast_changed": False, "records": [],
            "published_count": 0, "frozen_count": 0, "ineligible_count": 0,
            "validation_error_count": 0}


def capture(root, publication_path, observation_path, now=None, git=None, clock=None):
    """Freeze only newly published exact blobs with verified ORIGINAL observations.

    The observation can establish early retrievability of the ORIGINAL but is
    explicitly not the first remote receipt of the derived candidate.
    """
    root = Path(root)
    publication_path = Path(publication_path)
    observation_path = Path(observation_path)
    if (publication_path.is_symlink() or not publication_path.is_file() or
            publication_path.stat().st_size > 50000):
        return _empty("no_publication")
    publication = json.loads(publication_path.read_bytes())
    if type(publication) is not dict or publication.get("outcome") != "pushed_to_main":
        return _empty("no_confirmed_publication")
    sha = publication.get("commit_sha")
    count = publication.get("added_forecasts")
    if (type(sha) is not str or not SHA40.fullmatch(sha) or
            type(count) is not int or not 1 <= count <= 500):
        raise ValueError("invalid_publication_proof")
    if (observation_path.is_symlink() or not observation_path.is_file() or
            observation_path.stat().st_size > 500000):
        return _empty("no_original_remote_observation")
    obs = json.loads(observation_path.read_bytes())
    if (type(obs) is not dict or obs.get("schema") !=
            "FOUR_MODE_GITHUB_REMOTE_OBSERVATION_V1" or
            obs.get("publication_commit_sha") != sha or
            type(obs.get("records")) is not list):
        raise ValueError("wrong_or_untrusted_original_observation")
    receipts = {}
    for item in obs["records"]:
        code = item.get("race_code") if isinstance(item, dict) else None
        if not isinstance(code, str) or code in receipts:
            raise ValueError("duplicate_or_bad_observation")
        receipts[code] = item
    command = git or (lambda args: subprocess.check_output(
        ["git", *args], cwd=root, timeout=30))
    def run(*args):
        out = command(list(args))
        if type(out) is str:
            out = out.encode("utf-8")
        if type(out) is not bytes:
            raise ValueError("git_output_not_bytes")
        return out
    if run("rev-parse", "HEAD").decode().strip() != sha:
        raise ValueError("wrong_head")
    names = run("diff-tree", "--no-commit-id", "--name-only", "--diff-filter=A",
                "-r", sha, "--", "four_mode_forecasts/").decode().splitlines()
    if (len(names) != count or len(set(names)) != count or
            any(FORECAST_PATH.fullmatch(n) is None for n in names) or
            set(receipts) != {FORECAST_PATH.fullmatch(n).group(1) for n in names}):
        raise ValueError("first_add_and_observation_roster_disagree")
    now = now or datetime.now(JST)
    if now.utcoffset() != timedelta(hours=9):
        raise ValueError("invalid_now")
    result = _empty("original_published_candidate_research_artifact")
    result["publication_commit_sha"] = sha
    result["published_count"] = count
    result["candidate_method_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    result["at_jst"] = now.isoformat()
    for name in sorted(names):
        code = FORECAST_PATH.fullmatch(name).group(1)
        item = {"race_code": code, "status": "ineligible", "formal": False}
        try:
            original = run("show", sha + ":" + name)
            path = root/name
            if (path.is_symlink() or not path.is_file() or path.stat().st_size > 30000
                    or path.read_bytes() != original):
                raise ValueError("first_add_blob_changed")
            digest = hashlib.sha256(original).hexdigest()
            archive = json.loads(original)
            deadline = at_jst(archive.get("deadline_jst"))
            generated = at_jst(archive.get("generated_at_jst"))
            title_received = at_jst(archive.get("source_title_received_jst"))
            cards_received = at_jst(archive.get("source_cards_received_jst"))
            cutoff = deadline - timedelta(minutes=12)
            item.update({"source_forecast_sha256": digest,
                         "candidate_last_safe_jst": cutoff.isoformat(),
                         "deadline_jst": deadline.isoformat()})
            if code[:8] < "20261107":
                item["reason"] = "discovery_period_or_before_registration"
            elif deadline.strftime("%Y%m%d") != code[:8]:
                item["reason"] = "wrong_deadline_day"
            elif not (max(title_received, cards_received) <= generated < cutoff):
                item["reason"] = "source_generation_chronology_invalid"
            elif not generated < now < cutoff:
                item["reason"] = "not_frozen_strictly_before_T_minus_12"
            elif (receipts[code].get("status") != "github_server_observed_before_t_minus_12"
                  or receipts[code].get("first_add_blob_matches_remote") is not True
                  or receipts[code].get("original_sha256") != digest
                  or receipts[code].get("first_add_commit") != sha):
                item["reason"] = "original_remote_observation_not_verified"
            else:
                original_observed_utc = datetime.fromisoformat(receipts[code]["github_api_server_date_utc"])
                if (original_observed_utc.utcoffset() != timedelta(0) or
                        generated + timedelta(seconds=1) >= original_observed_utc or
                        original_observed_utc + timedelta(seconds=1) >= now):
                    item["reason"] = "original_observation_candidate_chronology_not_proven"
                    result["records"].append(item)
                    continue
                baseline, candidate = candidate_modes(archive)
                top1_pair = top1_pair_candidate(archive, baseline)
                # Prevent a concurrent clock crossing T-12 while selecting.
                finish = (clock() if clock is not None else datetime.now(JST))
                if (finish.utcoffset() != timedelta(hours=9) or not now < finish < cutoff):
                    item["reason"] = "freeze_time_or_cutoff_ambiguous"
                else:
                    item.update({
                        "status": "frozen_local_before_T_minus_12_research_only",
                        "source_generated_at_jst": generated.isoformat(),
                        "original_observed_at_utc": original_observed_utc.isoformat(),
                        "frozen_at_jst": finish.isoformat(),
                        "baseline": baseline, "candidate": candidate,
                        "top1_pair_candidate": top1_pair,
                        "top1_pair_rule": TOP1_PAIR_RULE,
                        "top1_selector_sha256": result["candidate_method_sha256"],
                        "mode_selector_sha256": {m: result["candidate_method_sha256"]
                                                 for m in SIZES},
                        "remote_first_receipt_of_candidate": False,
                        "official_beforeinfo_six_verified": False,
                        "official_odds_120_verified": False,
                        "warning": "Observation is of original, not candidate. Official 6-boat and odds proof unavailable.",
                    })
        except (ValueError, OSError, KeyError, TypeError, UnicodeError,
                subprocess.CalledProcessError, OverflowError) as exc:
            item = {"race_code": code, "status": "validation_error",
                    "error_type": type(exc).__name__, "formal": False}
        result["records"].append(item)
    result["frozen_count"] = sum(r["status"] ==
        "frozen_local_before_T_minus_12_research_only" for r in result["records"])
    result["ineligible_count"] = sum(r["status"] == "ineligible" for r in result["records"])
    result["validation_error_count"] = sum(r["status"] == "validation_error" for r in result["records"])
    if sum(result[k] for k in ("frozen_count", "ineligible_count",
                             "validation_error_count")) != count:
        raise ValueError("record_partition_mismatch")
    return result



def audit_historical_input_day(root, day):
    """Replay all saved originals WITHOUT reading results; not an accuracy test."""
    if not isinstance(day,str) or not re.fullmatch(r"20[0-9]{6}",day):
        raise ValueError("invalid_historical_day")
    root=Path(root)
    files=sorted((root/"four_mode_forecasts").glob(day+"*.json"))
    out={"schema":"FOUR_MODE_SHADOW_RESULT_BLIND_INPUT_REPLAY_V1",
         "day":day,"formal":False,"result_files_read":False,
         "original_v2_races":0,"excluded":{},
         "top1_pair_changes":{m:{"changed_top1":0,"preserved_top3_5_10":0}
                               for m in SIZES},
         "changes":{m:{
             "changed_all_tickets":0, "changed_top1":0,"changed_top3":0,
             "changed_top5":0,"changed_top10":0} for m in SIZES}}
    excluded={}
    for path in files:
        if (path.is_symlink() or not path.is_file() or path.stat().st_size>30000
                or not re.fullmatch(day+r"(?:0[1-9]|1[0-9]|2[0-4])(?:0[1-9]|1[0-2])",path.stem)):
            excluded["unsafe_or_nonrace_file"]=excluded.get("unsafe_or_nonrace_file",0)+1
            continue
        try:
            saved=json.loads(path.read_bytes())
            if saved.get("model_version")!=VERSION or saved.get("race_code")!=path.stem:
                raise ValueError("version_or_race_mismatch")
            base,candidate=candidate_modes(saved)
            top1_pair=top1_pair_candidate(saved,base)
        except (OSError,UnicodeError,TypeError,KeyError,ValueError,OverflowError,AssertionError) as exc:
            label=str(exc)[:60] or type(exc).__name__
            excluded[label]=excluded.get(label,0)+1
            continue
        out["original_v2_races"]+=1
        for m in SIZES:
            pair_stat=out["top1_pair_changes"][m]
            pair_stat["changed_top1"]+=int(base[m][0]!=top1_pair[m][0])
            pair_stat["preserved_top3_5_10"]+=int(all(
                set(base[m][:n])==set(top1_pair[m][:n]) for n in (3,5,10)))
            row=out["changes"][m]
            row["changed_all_tickets"]+=int(base[m]!=candidate[m])
            for k in (1,3,5,10):
                row[f"changed_top{k}"]+=int(base[m][:k]!=candidate[m][:k])
    out["excluded"]=dict(sorted(excluded.items()))
    out["status"]="historical_input_replay_only" if out["original_v2_races"] else "no_reproducible_v2_originals"
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", default=".")
    p.add_argument("--publication", default="four-mode-evidence/publication.json")
    p.add_argument("--observation", default="four-mode-evidence/github-server-observation.json")
    p.add_argument("--output", default="four-mode-evidence/all-mode-shadow.json")
    p.add_argument("--audit-historical-input-day")
    a = p.parse_args()
    if a.audit_historical_input_day:
        print("FOUR_MODE_SHADOW_HISTORICAL_INPUT=" + json.dumps(
            audit_historical_input_day(a.root,a.audit_historical_input_day),
            ensure_ascii=False,sort_keys=True))
        return
    report = capture(a.root,a.publication,a.observation)
    out=Path(a.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.is_symlink():
        raise ValueError("unsafe_output_symlink")
    with out.open("x",encoding="utf-8") as f:
        json.dump(report,f,ensure_ascii=False,sort_keys=True,indent=2)
        f.write("\n")
    print("FOUR_MODE_ALL_MODE_SHADOW=" + json.dumps({
        k:report[k] for k in ("status","published_count","frozen_count",
                             "ineligible_count","validation_error_count")},sort_keys=True))
    if report["validation_error_count"]:
        raise SystemExit(2)


if __name__=="__main__":
    main()
