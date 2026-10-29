#!/usr/bin/env python3
"""Read-only race-key inventory for legacy -> CLEAN. No copies, deletions or scoring."""
import argparse
import json
import os
import re
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

LEGACY = "ikst2512-eng/boat-edge"
CLEAN = "ikst2512-eng/boat-edge-clean"
PREFIXES = ("data/site_prediction_snapshots/", "data/site_prediction_audit/",
            "data/site_prediction_history/", "data/site_results/",
            "data/site_odds/", "data/raw/")
CLEAN_PREFIXES = ("confirmed_results/", "four_mode_forecasts/",
                  "prospective_predictions/", "four_mode_performance/")
LEGACY_NAME = re.compile(r"^(\d{8})-(\d{2})-(\d{2})\.json$")
CLEAN_NAME = re.compile(r"^(\d{8})(\d{2})(\d{2})\.json$")


def fetch_tree(repo, ref):
    url = f"https://api.github.com/repos/{repo}/git/trees/{ref}?recursive=1"
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "clean-legacy-crosswalk"}
    if os.getenv("GH_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["GH_TOKEN"]
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=60) as response:
        doc = json.load(response)
    if doc.get("truncated"):
        raise RuntimeError(f"GitHub recursive tree truncated: {repo}; stop, do not trust counts")
    if not doc.get("sha") or not isinstance(doc.get("tree"), list):
        raise RuntimeError(f"Invalid tree response: {repo}")
    return doc


def race_code(path, legacy):
    filename = Path(path).name
    match = (LEGACY_NAME if legacy else CLEAN_NAME).fullmatch(filename)
    if not match:
        return None
    date, venue, race = match.groups()
    if not (1 <= int(venue) <= 24 and 1 <= int(race) <= 12):
        return None
    try:
        datetime.strptime(date, "%Y%m%d")
    except ValueError:
        return None
    return date + venue + race


def inventory(tree, prefixes, legacy):
    indexed = defaultdict(list)
    unparsed = defaultdict(int)
    counts = defaultdict(int)
    for obj in tree["tree"]:
        if obj.get("type") != "blob":
            continue
        path = obj.get("path", "")
        prefix = next((p for p in prefixes if path.startswith(p)), None)
        if prefix is None:
            continue
        counts[prefix] += 1
        code = race_code(path, legacy)
        if code is None:
            unparsed[prefix] += 1
        else:
            indexed[code].append({"path": path, "git_blob_sha1": obj["sha"],
                                  "category": prefix})
    return indexed, counts, unparsed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--legacy-ref", default="main")
    parser.add_argument("--clean-ref", default="main")
    parser.add_argument("--output", default="legacy_race_crosswalk.json")
    args = parser.parse_args()
    legacy_tree = fetch_tree(LEGACY, args.legacy_ref)
    clean_tree = fetch_tree(CLEAN, args.clean_ref)
    legacy, legacy_counts, legacy_unparsed = inventory(legacy_tree, PREFIXES, True)
    clean, clean_counts, clean_unparsed = inventory(clean_tree, CLEAN_PREFIXES, False)
    common = sorted(set(legacy) & set(clean))
    records = []
    for code in common:
        records.append({"race_code": code, "legacy": legacy[code], "clean": clean[code],
                        "status": "SAME_RACE_ONLY_CONTENT_NOT_VERIFIED",
                        "sha256_verified": False,
                        "prediction_equivalence_verified": False,
                        "deadline_provenance_verified": False})
    # Do not mistake absence from CLEAN for a reason to copy legacy files.
    # Only races actually present in CLEAN are candidates for evidence linkage.
    # Other races remain in the legacy repository until their value is decided,
    # but are excluded from every automatic migration/backup queue.
    needed_provenance = sorted(set(legacy) & set(clean))
    no_clean_reference = sorted(set(legacy) - set(clean))
    evidence_link_candidates = [
        {"race_code": code, "legacy": legacy[code], "clean": clean[code],
         "decision": "REVIEW_EVIDENCE_LINK_ONLY",
         "copy_authorized": False}
        for code in needed_provenance
    ]
    # Minimal provenance selection: only CLEAN's prospective forecasts and
    # matching legacy prediction/audit/history records are NOT equivalent predictions.
    # Only use them when a specific historical validation requires source proof.
    # Do not auto-import
    # legacy odds, results, raw inputs, or site-autopilot snapshots.
    provenance_categories = {
        "data/site_prediction_snapshots/",
        "data/site_prediction_audit/",
        "data/site_prediction_history/",
    }
    prospective_provenance_candidates = []
    for code in sorted(set(legacy) & set(clean)):
        current = [row for row in clean[code]
                   if row["category"] == "prospective_predictions/"]
        originals = [row for row in legacy[code]
                     if row["category"] in provenance_categories]
        if current and originals:
            prospective_provenance_candidates.append({
                "race_code": code, "clean": current, "legacy": originals,
                "decision": "CROSS_MODEL_ONLY_NO_IMPORT_UNLESS_HISTORICAL_EVALUATION_REQUIRES_IT",
                "copy_authorized": False,
                "legacy_prediction_logic_import_authorized": False,
            })
    document = {
        "schema": "CLEAN_LEGACY_RACE_CROSSWALK_V2",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "legacy_repo": LEGACY, "legacy_ref": args.legacy_ref,
        "legacy_tree_sha": legacy_tree["sha"],
        "clean_repo": CLEAN, "clean_ref": args.clean_ref,
        "clean_tree_sha": clean_tree["sha"],
        "legacy_prefix_file_counts": dict(sorted(legacy_counts.items())),
        "clean_prefix_file_counts": dict(sorted(clean_counts.items())),
        "unparsed_legacy_files": dict(sorted(legacy_unparsed.items())),
        "unparsed_clean_files": dict(sorted(clean_unparsed.items())),
        "matched_race_count": len(common),
        "legacy_only_race_count": len(set(legacy)-set(clean)),
        "clean_only_race_count": len(set(clean)-set(legacy)),
        "matched_races": records,
        "evidence_link_candidates": evidence_link_candidates,
        "prospective_provenance_candidates": prospective_provenance_candidates,
        "prospective_provenance_candidate_count": len(prospective_provenance_candidates),
        "no_clean_reference_count": len(no_clean_reference),
        # Actionable read-only preservation queue: every legacy-only race keeps its
        # source paths and immutable Git blob IDs for later byte-level verification.
        "legacy_only_races": [
            {"race_code": code, "legacy": legacy[code],
             "status": "NOT_NEEDED_FOR_CURRENT_CLEAN_RACE_SET_REVIEW_BEFORE_RETIREMENT",
             "copy_authorized": False}
            for code in sorted(set(legacy) - set(clean))
        ],
        "warning": "Git blob SHA-1 is NOT SHA-256; same race is NOT proof of equal predictions, preserved provenance, or safe deletion.",
        "delete_authorized": False
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: document[key] for key in
                      ("matched_race_count", "legacy_only_race_count", "clean_only_race_count")},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
