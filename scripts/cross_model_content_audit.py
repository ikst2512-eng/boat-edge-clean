#!/usr/bin/env python3
"""Read-only cross-model audit. Never imports forecasts or authorizes deletion.

Input: JSON created by scripts/legacy_race_crosswalk.py
Output: separate machine-readable comparisons of the candidate race records.
Requires GitHub API access (GH_TOKEN recommended for private repos/rate limits).
"""
import argparse
import base64
import hashlib
import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

MODEL_KEYS = ("model_version", "model_id", "model", "prediction_model", "version")
PICK_KEYS = ("combination", "trifecta", "bet", "ticket", "buy", "kumi", "組番", "買い目")


def fetch_blob(repo, sha):
    url = f"https://api.github.com/repos/{repo}/git/blobs/{sha}"
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "clean-cross-model-content-audit"}
    if os.environ.get("GH_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["GH_TOKEN"]
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=45) as resp:
        result = json.load(resp)
    if result.get("encoding") != "base64" or not isinstance(result.get("content"), str):
        raise ValueError("Unsupported GitHub blob encoding")
    raw = base64.b64decode(result["content"])
    if hashlib.sha1(b"blob " + str(len(raw)).encode() + bytes([0]) + raw).hexdigest() != sha:
        raise ValueError("Git blob object identity mismatch")
    return raw


def find_models(obj):
    values = set()
    def walk(node):
        if isinstance(node, dict):
            for k, v in node.items():
                if k in MODEL_KEYS and isinstance(v, (str, int, float)):
                    values.add(str(v))
                elif isinstance(v, (dict, list)):
                    walk(v)
        elif isinstance(node, list):
            for entry in node:
                walk(entry)
    walk(obj)
    return sorted(values)


def extract_top10(obj):
    """Conservative: only explicit rank-ordered arrays; never infer from arbitrary lists."""
    if not isinstance(obj, dict):
        return None
    for key in ("top10", "top_10", "top_picks", "ranked_predictions", "predictions"):
        seq = obj.get(key)
        if not isinstance(seq, list) or len(seq) < 10:
            continue
        result = []
        for item in seq[:10]:
            val = item if isinstance(item, str) else (
                next((item[k] for k in PICK_KEYS if k in item), None)
                if isinstance(item, dict) else None
            )
            if isinstance(val, (list, tuple)) and len(val) == 3:
                val = "-".join(map(str, val))
            if not isinstance(val, str):
                break
            digits = val.replace("-", "").replace(" ", "")
            if len(digits) != 3 or any(d not in "123456" for d in digits) or len(set(digits)) != 3:
                break
            result.append("-".join(digits))
        if len(result) == 10 and len(set(result)) == 10:
            return result
    return None


def inspect(repo, entry):
    raw = fetch_blob(repo, entry["git_blob_sha1"])
    record = {"path": entry["path"], "git_blob_sha1": entry["git_blob_sha1"],
              "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
    try:
        obj = json.loads(raw)
        record["models"] = find_models(obj)
        record["top10"] = extract_top10(obj)
        record["parse_status"] = "JSON_OK"
    except (ValueError, UnicodeError) as exc:
        record["models"] = []
        record["top10"] = None
        record["parse_status"] = type(exc).__name__
    return record


def audit(doc):
    if doc.get("schema") != "CLEAN_LEGACY_RACE_CROSSWALK_V2":
        raise ValueError("Expected CLEAN_LEGACY_RACE_CROSSWALK_V2 input")
    output = []
    cache = {}
    def cached(repo, entry):
        key = (repo, entry["git_blob_sha1"])
        if key not in cache:
            cache[key] = inspect(repo, entry)
        return cache[key]
    # Cover every matched race, rather than only prospective provenance candidates.
    # Select prediction evidence only; never confuse odds/results/raw records
    # with a forecast or claim that unrelated blobs prove forecast equivalence.
    prediction_prefixes = ("data/site_prediction_snapshots/",
                           "data/site_prediction_audit/",
                           "data/site_prediction_history/")
    # Compare legacy to the separately versioned CLEAN prospective model only.
    # Four-mode forecasts are a distinct cohort and must not inflate this count.
    clean_prefixes = ("prospective_predictions/",)
    for matched in doc["matched_races"]:
        candidate = {
            "race_code": matched["race_code"],
            "legacy": [x for x in matched["legacy"]
                       if x["category"] in prediction_prefixes],
            "clean": [x for x in matched["clean"]
                      if x["category"] in clean_prefixes],
        }
        code = candidate["race_code"]
        record = {"race_code": code, "legacy": [], "clean": [],
                  "copy_authorized": False, "delete_authorized": False}
        failures = []
        for label, repo in (("legacy", doc["legacy_repo"]), ("clean", doc["clean_repo"])):
            for entry in candidate[label]:
                try:
                    record[label].append(cached(repo, entry))
                except Exception as exc:
                    failures.append({"side": label, "path": entry["path"],
                                     "error": str(exc)[:250]})
        record["errors"] = failures
        legacy_models = sorted({m for x in record["legacy"] for m in x["models"]})
        clean_models = sorted({m for x in record["clean"] for m in x["models"]})
        record["legacy_models"] = legacy_models
        record["clean_models"] = clean_models
        pairs = [(a, b) for a in record["legacy"] for b in record["clean"]]
        record["sha256_equal_pairs"] = [
            [a["path"], b["path"]] for a, b in pairs if a["sha256"] == b["sha256"]
        ]
        top_pairs = [(a, b) for a, b in pairs if a["top10"] and b["top10"]]
        record["top10_comparisons"] = [
            {"legacy_path": a["path"], "clean_path": b["path"],
             "same_rank_positions": sum(x == y for x, y in zip(a["top10"], b["top10"])),
             "overlapping_tickets": len(set(a["top10"]) & set(b["top10"]))}
            for a, b in top_pairs
        ]
        record["decision"] = (
            "REVIEW_FETCH_ERRORS" if failures else
            "NO_COMPARABLE_FORECAST_EVIDENCE" if not record["legacy"] or not record["clean"] else
            "CROSS_MODEL_DISTINCT_NO_IMPORT" if legacy_models and clean_models
            and not set(legacy_models).intersection(clean_models) else
            "REVIEW_CONTENT_AND_PROVENANCE_NO_IMPORT"
        )
        record["historical_evidence_required_proven"] = False
        output.append(record)
    return {
        "schema": "CLEAN_CROSS_MODEL_CONTENT_AUDIT_V1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_tree_shas": {"legacy": doc["legacy_tree_sha"], "clean": doc["clean_tree_sha"]},
        "matched_race_count": len(output), "candidate_count": len(output),
        "compared_race_count": sum(bool(r["top10_comparisons"]) for r in output),
        "content_read_race_count": sum(bool(r["legacy"]) and bool(r["clean"]) and not r["errors"] for r in output),
        "no_comparable_evidence_count": sum(r["decision"] == "NO_COMPARABLE_FORECAST_EVIDENCE" for r in output),
        "unresolved_count": sum(bool(r["errors"]) for r in output),
        "races": output, "copy_authorized": False, "delete_authorized": False,
        "warning": "Same race or same ticket does not prove model equivalence. Missing top10 is UNKNOWN, not equal. No historical necessity inferred."
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--crosswalk", required=True)
    p.add_argument("--output", required=True)
    a = p.parse_args()
    document = audit(json.loads(Path(a.crosswalk).read_text(encoding="utf-8")))
    dest = Path(a.output)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: document[k] for k in ("candidate_count", "content_read_race_count", "compared_race_count", "no_comparable_evidence_count", "unresolved_count")}))


if __name__ == "__main__":
    main()
