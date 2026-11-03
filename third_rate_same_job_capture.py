"""Freeze third-rate shadow alongside existing post-push hole shadow in same job.

Artifact-only, research-only, never a production prediction or remote first-
seen proof. Record exact tickets before T-12 or mark the race ineligible.
"""
import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

from clean_four_modes import rank_modes
from four_mode_archive_api import archived_four_modes
from four_mode_v2_third_rate_shadow import (
    FUTURE_START_JST, LOCKED_PROTOCOL_MAIN_SHA, PROTOCOL, VERSION, candidate,
)
from research_model import probabilities

SHA = re.compile(r"[0-9a-f]{40}\Z")
FILE = re.compile(r"four_mode_forecasts/(20[0-9]{10})\.json\Z")
JST = timezone(timedelta(hours=9))


def freeze_published(root, evidence_path, now=None, git=None, clock=None):
    root = Path(root)
    evidence_path = Path(evidence_path)
    result = {
        "schema": "V2_THIRD_RATE_SAME_JOB_FROZEN_SHADOW_V1",
        "protocol": PROTOCOL,
        "lock_main_commit": LOCKED_PROTOCOL_MAIN_SHA,
        "status": "no_confirmed_publication",
        "formal": False,
        "independent_remote_first_seen_verified": False,
        "production_forecast_changed": False,
        "records": [],
        "published_forecasts": 0,
        "frozen_before_t_minus_12": 0,
        "ineligible_count": 0,
        "validation_error_count": 0,
    }
    if evidence_path.is_symlink() or not evidence_path.is_file():
        return result
    publication = json.loads(evidence_path.read_text(encoding="utf-8"))
    if not isinstance(publication, dict):
        raise ValueError("invalid_publication_file")
    if publication.get("outcome") != "pushed_to_main":
        return result
    sha = publication.get("commit_sha")
    count = publication.get("added_forecasts")
    if not isinstance(sha, str) or not SHA.fullmatch(sha) or (
            type(count) is not int or not 1 <= count <= 500):
        raise ValueError("invalid_publication_claim")
    fixed_test_clock = now is not None
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("naive_capture_time")
    clock = clock or (lambda: now if fixed_test_clock else datetime.now(timezone.utc))
    git = git or (lambda args: subprocess.check_output(
        ["git", *args], cwd=root, text=True, timeout=30))
    if git(["rev-parse", "HEAD"]).strip() != sha:
        raise ValueError("publication_commit_not_checkout_head")
    names = git(["diff-tree", "--no-commit-id", "--name-only", "--diff-filter=A",
                 "-r", sha, "--", "four_mode_forecasts/"]).splitlines()
    if len(names) != count or len(set(names)) != len(names) or any(
            not FILE.fullmatch(name) for name in names):
        raise ValueError("published_first_add_roster_mismatch")
    result["published_forecasts"] = count
    result["status"] = "captured_local_after_push_not_remote_proven"
    result["publication_commit_sha"] = sha
    result["capture_at_utc"] = now.astimezone(timezone.utc).isoformat()
    for name in sorted(names):
        code = FILE.fullmatch(name).group(1)
        record = {"race_code": code, "status": "ineligible"}
        path = root / name
        try:
            if code[:8] < FUTURE_START_JST:
                record["reason"] = "development_period"
            elif path.is_symlink() or not path.is_file() or path.stat().st_size > 30000:
                record["reason"] = "missing_or_unsafe_source_archive"
            else:
                original = git(["show", sha + ":" + name]).encode("utf-8")
                current = path.read_bytes()
                if original != current:
                    raise ValueError("first_add_blob_changed")
                record["source_forecast_sha256"] = hashlib.sha256(current).hexdigest()
                status, archive = archived_four_modes(code, root)
                if status != 200 or archive.get("model_version") != VERSION:
                    record["reason"] = "invalid_v2_archive"
                else:
                    deadline = datetime.fromisoformat(archive["deadline_jst"])
                    cutoff = deadline - timedelta(minutes=12)
                    record["t_minus_12_jst"] = cutoff.isoformat()
                    if deadline.utcoffset() != timedelta(hours=9):
                        record["reason"] = "invalid_deadline_timezone"
                    elif now >= cutoff:
                        record["reason"] = "after_t_minus_12"
                    else:
                        raw = json.loads(current.decode("utf-8"))
                        rates = raw["input_national_win_rates"]
                        board = probabilities(rates)
                        modes = rank_modes(board)
                        if any(
                            [(x["combo"], x["p"]) for x in archive["modes"][mode]["tickets"]]
                            != [(x["combo"], x["p"]) for x in modes[mode]["tickets"]]
                            for mode in ("narrow", "hit", "balance", "hole")
                        ):
                            raise ValueError("saved_forecast_not_reproducible")
                        baseline = [x["combo"] for x in archive["modes"]["hit"]["tickets"]]
                        picks, _ = candidate(baseline, rates, board)
                        finished_at = clock()
                        if finished_at.tzinfo is None:
                            raise ValueError("naive_finished_time")
                        if finished_at >= cutoff:
                            record["reason"] = "calculation_crossed_t_minus_12"
                        else:
                            record.update({
                                "status": "frozen_in_same_job_before_t_minus_12",
                                "baseline_top10": baseline,
                                "candidate_top10": picks,
                                "frozen_at_utc": finished_at.astimezone(timezone.utc).isoformat(),
                                "source_commit_sha": sha,
                                "protocol": PROTOCOL,
                                "formal": False,
                            })
        except (ValueError, TypeError, KeyError, UnicodeError,
                subprocess.CalledProcessError, OSError) as exc:
            record = {"race_code": code, "status": "validation_error",
                      "error_type": type(exc).__name__}
        result["records"].append(record)
    result["frozen_before_t_minus_12"] = sum(
        row["status"] == "frozen_in_same_job_before_t_minus_12"
        for row in result["records"])
    result["ineligible_count"] = count - result["frozen_before_t_minus_12"]
    result["validation_error_count"] = sum(
        row["status"] == "validation_error" for row in result["records"])
    if len(result["records"]) != count:
        raise ValueError("record_partition")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--evidence", default="four-mode-evidence/publication.json")
    parser.add_argument("--output", default="four-mode-evidence/third-rate-shadow.json")
    args = parser.parse_args()
    try:
        evidence = freeze_published(args.root, args.evidence)
    except (ValueError, KeyError, TypeError, OSError, UnicodeError,
            subprocess.CalledProcessError) as exc:
        evidence = {
            "schema": "V2_THIRD_RATE_SAME_JOB_FROZEN_SHADOW_V1",
            "status": "validation_error_before_freeze",
            "formal": False, "production_forecast_changed": False,
            "independent_remote_first_seen_verified": False,
            "published_forecasts": 0, "frozen_before_t_minus_12": 0,
            "ineligible_count": 0, "validation_error_count": 1,
            "error_type": type(exc).__name__, "records": [],
        }
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Created in the original capture job's artifact only; never staged in main.
    path.write_text(json.dumps(evidence, ensure_ascii=False, sort_keys=True,
                               indent=2) + "\n", encoding="utf-8")
    print("THIRD_RATE_SAME_JOB_SHADOW=" + json.dumps({
        "status": evidence["status"],
        "published_forecasts": evidence["published_forecasts"],
        "frozen_before_t_minus_12": evidence["frozen_before_t_minus_12"],
        "ineligible_count": evidence["ineligible_count"],
        "validation_error_count": evidence["validation_error_count"],
    }, sort_keys=True))
    if evidence["validation_error_count"]:
        raise SystemExit(2)
