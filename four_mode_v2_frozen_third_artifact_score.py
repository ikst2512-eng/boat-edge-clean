"""Score only truly frozen third-rate shadow tickets from an Actions artifact.

No after-result model regeneration. Existing local Git archive is used only
to compare SHA256 of frozen original; compare_race supplies confirmed finish.
Artifact retrieval/first remote publication remain independently unverified.
"""
import argparse
import hashlib
import json
import re
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from four_mode_frozen_diagnostic import compare_race
from four_mode_v2_third_rate_shadow import PROTOCOL

SCHEMA = "V2_THIRD_RATE_SAME_JOB_FROZEN_SHADOW_V1"
FUTURE_START = "20261104"
RACE = re.compile(r"20[0-9]{10}\Z")
SHA = re.compile(r"[a-f0-9]{40}\Z")
HEX = re.compile(r"[a-f0-9]{64}\Z")
VALID = {"-".join((str(a), str(b), str(c)))
         for a in range(1, 7) for b in range(1, 7) for c in range(1, 7)
         if len({a, b, c}) == 3}


def _tickets(value):
    return (type(value) is list and len(value) == 10
            and all(type(x) is str and x in VALID for x in value)
            and len(set(value)) == 10)


def score_evidence(evidence, root):
    """One same-job artifact, tied to archived V2 bytes; never formal accuracy."""
    root = Path(root)
    if (type(evidence) is not dict or evidence.get("schema") != SCHEMA
            or evidence.get("protocol") != PROTOCOL
            or evidence.get("formal") is not False
            or evidence.get("independent_remote_first_seen_verified") is not False
            or evidence.get("production_forecast_changed") is not False):
        raise ValueError("invalid_shadow_evidence")
    records = evidence.get("records")
    if type(records) is not list or len(records) > 500:
        raise ValueError("invalid_shadow_records")
    published = evidence.get("published_forecasts")
    if type(published) is not int or published < 0 or published > 500:
        raise ValueError("invalid_publication_count")
    if len(records) != published:
        raise ValueError("artifact_publication_roster_inconsistent")
    if (type(evidence.get("frozen_before_t_minus_12")) is not int
            or sum(r.get("status") == "frozen_in_same_job_before_t_minus_12"
                   for r in records) != evidence["frozen_before_t_minus_12"]):
        raise ValueError("artifact_frozen_count_inconsistent")
    if (type(evidence.get("ineligible_count")) is not int
            or evidence["ineligible_count"] != published - evidence["frozen_before_t_minus_12"]):
        raise ValueError("artifact_ineligible_count_inconsistent")
    # Explicit no-new-publication evidence is a valid zero denominator.
    if published == 0 and evidence.get("status") not in (
            "no_confirmed_publication", "validation_error_before_freeze"):
        raise ValueError("invalid_empty_publication_status")
    if published > 0 and (evidence.get("status") != "captured_local_after_push_not_remote_proven"
                          or not SHA.fullmatch(str(evidence.get("publication_commit_sha")))):
        raise ValueError("invalid_publication_reference")
    scores = {f"top{n}": {"baseline": 0, "candidate": 0,
                           "gained": 0, "lost": 0} for n in (3, 5, 10)}
    out = {"status": "frozen_artifact_result_comparison_research_only",
           "formal": False, "independent_first_publication_verified": False,
           "untouched_holdout_verified": False, "production_promotion_allowed": False,
           "published_forecasts": published,
           "publication_evidence_status": evidence["status"],
           "validation_error_count": evidence.get("validation_error_count", 0),
           "frozen": 0, "paired": 0, "pending_results": 0,
           "excluded": 0, "invalid": 0, "race_codes_paired": [], "paired_race_scores": [],
           "race_codes_frozen": [],
           "topn": scores, "warning": "Results scored ONLY from same-job frozen artifact, not independently timestamped publication."}
    seen = set()
    for item in records:
        if type(item) is not dict:
            raise ValueError("malformed_record")
        code = item.get("race_code")
        if type(code) is not str or not RACE.fullmatch(code) or code in seen:
            raise ValueError("invalid_or_duplicate_race")
        seen.add(code)
        if item.get("status") != "frozen_in_same_job_before_t_minus_12":
            out["excluded"] += 1
            continue
        out["frozen"] += 1
        out["race_codes_frozen"].append(code)
        try:
            if code[:8] < FUTURE_START or item.get("protocol") != PROTOCOL:
                raise ValueError("development_or_protocol_mismatch")
            if item.get("source_commit_sha") != evidence["publication_commit_sha"]:
                raise ValueError("source_commit_mismatch")
            if not _tickets(item.get("baseline_top10")) or not _tickets(item.get("candidate_top10")):
                raise ValueError("invalid_frozen_tickets")
            timestamp = datetime.fromisoformat(item["frozen_at_utc"])
            cutoff = datetime.fromisoformat(item["t_minus_12_jst"])
            if (timestamp.utcoffset() is None or cutoff.utcoffset() != timedelta(hours=9)
                    or timestamp >= cutoff or cutoff.strftime("%Y%m%d") != code[:8]):
                raise ValueError("frozen_timing_invalid")
            path = root / "four_mode_forecasts" / (code + ".json")
            if (path.is_symlink() or not path.is_file()
                    or path.stat().st_size > 30000
                    or not HEX.fullmatch(str(item.get("source_forecast_sha256")))
                    or hashlib.sha256(path.read_bytes()).hexdigest() != item["source_forecast_sha256"]):
                raise ValueError("original_forecast_digest_mismatch")
            archive = json.loads(path.read_text(encoding="utf-8"))
            if (archive.get("race_code") != code or
                    archive.get("model_version") != "CLEAN_FOUR_MODES_V2_PROVISIONAL_UNCALIBRATED"
                    or [r.get("combo") for r in archive["modes"]["hit"]["tickets"]]
                    != item["baseline_top10"]):
                raise ValueError("original_baseline_mismatch")
        except (KeyError, ValueError, TypeError, OSError, UnicodeError):
            out["invalid"] += 1
            continue
        compared = compare_race(code, root)
        if compared.get("status") == "result_unavailable":
            out["pending_results"] += 1
            continue
        if compared.get("status") != "historical_comparison_only":
            out["invalid"] += 1
            continue
        winning = compared.get("winning_ticket")
        if type(winning) is not str or winning not in VALID:
            out["invalid"] += 1
            continue
        out["paired"] += 1
        out["race_codes_paired"].append(code)
        per_race = {"race_code": code, "topn": {}}
        out["paired_race_scores"].append(per_race)
        for n in (3, 5, 10):
            row = scores[f"top{n}"]
            base_hit = winning in item["baseline_top10"][:n]
            candidate_hit = winning in item["candidate_top10"][:n]
            row["baseline"] += int(base_hit)
            row["candidate"] += int(candidate_hit)
            row["gained"] += int(candidate_hit and not base_hit)
            row["lost"] += int(base_hit and not candidate_hit)
            per_race["topn"][f"top{n}"] = {
                "baseline": int(base_hit), "candidate": int(candidate_hit),
                "gained": int(candidate_hit and not base_hit),
                "lost": int(base_hit and not candidate_hit),
            }
    if out["frozen"] != out["paired"] + out["pending_results"] + out["invalid"]:
        raise ValueError("frozen_partition_mismatch")
    if out["frozen"] + out["excluded"] != published:
        raise ValueError("published_partition_mismatch")
    for row in scores.values():
        if row["candidate"] - row["baseline"] != row["gained"] - row["lost"]:
            raise ValueError("gain_loss_mismatch")
    out["race_codes_paired"].sort()
    out["paired_race_scores"].sort(key=lambda x: x["race_code"])
    out["race_codes_frozen"].sort()
    return out


def score_zip(zip_path, root):
    with zipfile.ZipFile(zip_path) as z:
        matches = [i for i in z.infolist() if i.filename == "four-mode-evidence/third-rate-shadow.json"
                   or i.filename == "third-rate-shadow.json"]
        if len(matches) != 1 or matches[0].file_size > 2000000:
            raise ValueError("missing_duplicate_or_oversized_third_shadow")
        data = json.loads(z.read(matches[0]).decode("utf-8"))
    return score_evidence(data, root)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-zip", required=True, type=Path)
    parser.add_argument("--root", default=".")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    report = score_zip(args.artifact_zip, args.root)
    args.output.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True,
                                      indent=2) + "\n", encoding="utf-8")
    print("V2_FROZEN_THIRD_SCORE=" + json.dumps(report, sort_keys=True))
