"""Bulk, immutable historical forecast-vs-outcome audit; NEVER promote models.

Legacy V133 (79 archived picks, old policy) uses pinned public result files
from the old repository. CLEAN V1/V2 are audited separately from their actual
frozen tickets, using verified existing confirmed_results. No retroactive
forecast generation, no live model changes, no pooling incompatible policies.
"""
import base64
import hashlib
import json
import math
import os
import re
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

from four_mode_frozen_diagnostic import compare_race

ROOT = Path(__file__).resolve().parents[1]
OLD_REPO = "ikst2512-eng/boat-edge"
PINNED_OLD_RESULTS_COMMIT = "7dd4ce6127d7e71298605015873030ff1168a8d3"
CODE = re.compile(r"20[0-9]{6}-[0-9]{2}-[0-9]{2}\.json\Z")
NEW_CODE = re.compile(r"20[0-9]{10}\Z")
MODES = ("narrow", "hit", "balance", "hole")
TOP = (1, 3, 5, 10)
JST = timezone(timedelta(hours=9))
ALLOWED_POLICIES = ("BALANCE10_WAVE12_15_18_V133_FIXED",
                    "PROVISIONAL_V254_THIRD_TAIL10_FIXED_TOP7")


def blob_sha(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def result_from_pinned_repo(key):
    token = os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
    url = ("https://api.github.com/repos/" + OLD_REPO + "/contents/data/site_results/"
           + quote(key + ".json") + "?ref=" + PINNED_OLD_RESULTS_COMMIT)
    headers = {"Accept": "application/vnd.github+json",
               "X-GitHub-Api-Version": "2022-11-28",
               "User-Agent": "boat-edge-legacy-79-bulk-audit"}
    if token:
        headers["Authorization"] = "Bearer " + token
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=35) as response:
        if response.status != 200:
            raise ValueError("result_http_not_200")
        raw = json.load(response)
    if (not isinstance(raw, dict) or raw.get("type") != "file"
            or raw.get("encoding") != "base64"
            or raw.get("path") != "data/site_results/" + key + ".json"):
        raise ValueError("invalid_result_provenance")
    data = base64.b64decode(raw["content"], validate=False)
    if blob_sha(data) != raw.get("sha") or len(data) > 20000:
        raise ValueError("result_blob_mismatch")
    return json.loads(data), raw["sha"]


def checked_result(result, key, deadline):
    if (result.get("schema_version") != "boat-edge-site-result-v109"
            or result.get("race_key") != key or result.get("status") != "confirmed"
            or not isinstance(result.get("source"), str)
            or not result["source"].startswith("https://www.boatrace.jp/")
            or type(result.get("finish_order")) is not list
            or len(result["finish_order"]) != 3
            or any(type(x) is not int or x not in range(1, 7)
                   for x in result["finish_order"])
            or len(set(result["finish_order"])) != 3
            or result.get("trifecta") != "-".join(map(str, result["finish_order"]))
            or type(result.get("trifecta_payout_yen_per_100")) is not int
            or result["trifecta_payout_yen_per_100"] <= 0):
        raise ValueError("invalid_official_result_record")
    seen = datetime.fromisoformat(result["fetched_at"])
    if seen.utcoffset() != timedelta(hours=9) or seen <= deadline:
        raise ValueError("official_result_published_before_deadline")
    return result["trifecta"]


def checked_legacy_forecast(record, key):
    if (record.get("schema_version") != "boat-edge-server-site-final-v123"
            or record.get("snapshot_window") != "FINAL_15M"
            or record.get("race_key") != key
            or record.get("prediction_kind") != "SITE_REFERENCE_V122"
            or record.get("selection_policy") != "V122_SCENARIO_AWARE_PROBABILITY_FIRST"
            or record.get("mode_policy") not in ALLOWED_POLICIES
            or record.get("guards") != {"results_seen": False, "unlock": False, "scoring": False}):
        raise ValueError("invalid_legacy_prediction_identity")
    date = key[:8]
    deadline = datetime.strptime(date + record["deadline"], "%Y%m%d%H:%M").replace(tzinfo=JST)
    at = datetime.fromisoformat(record["first_saved_at"])
    saved = datetime.fromisoformat(record["saved_at"])
    if (at.tzinfo is None or saved.tzinfo is None or saved < at
            or deadline - at <= timedelta(0) or deadline - at > timedelta(minutes=15)):
        raise ValueError("archived_prediction_outside_final15m")
    count = {"narrow": 3, "hit": 10, "balance": 10}
    modes = record["modes"]
    if not all(name in modes for name in MODES) or len(modes) not in (4, 5):
        raise ValueError("missing_legacy_modes")
    if len(modes["hole"]["tickets"]) not in (12, 15, 18):
        raise ValueError("invalid_legacy_hole_size")
    count["hole"] = len(modes["hole"]["tickets"])
    cleaned = {}
    for mode, number in count.items():
        rows = modes[mode]["tickets"]
        if len(rows) != number:
            raise ValueError("invalid_legacy_mode_size")
        combos = []
        for ticket in rows:
            combo = ticket.get("combo")
            if (not isinstance(combo, str)
                    or not re.fullmatch(r"[1-6]-[1-6]-[1-6]", combo)
                    or len(set(combo.split("-"))) != 3
                    or not isinstance(ticket.get("p"), (float, int))
                    or isinstance(ticket["p"], bool)
                    or not 0 <= ticket["p"] <= 100):
                raise ValueError("invalid_legacy_ticket")
            combos.append(combo)
        if len(set(combos)) != number:
            raise ValueError("duplicate_legacy_tickets")
        cleaned[mode] = combos
    return deadline, cleaned


def add_record(total, modes, winning):
    total["evaluated"] += 1
    for mode, picks in modes.items():
        d = total["modes"].setdefault(mode, {"hits": 0, "topn_hits": {str(x): 0 for x in TOP},
                                             "tickets_total": 0})
        d["tickets_total"] += len(picks)
        if winning in picks:
            d["hits"] += 1
            rank = picks.index(winning) + 1
            for n in TOP:
                d["topn_hits"][str(n)] += int(rank <= n)


def blank_group():
    return {"evaluated": 0, "modes": {}}


def summarize(group):
    n = group["evaluated"]
    result = {"evaluated": n, "modes": {}}
    for mode, v in sorted(group["modes"].items()):
        result["modes"][mode] = {
            **v, "hit_pct": round(100 * v["hits"]/n, 2) if n else None,
            "topn_pct": {k: round(100 * hits/n, 2) if n else None
                         for k, hits in v["topn_hits"].items()},
            "avg_tickets": round(v["tickets_total"]/n, 2) if n else None,
        }
    return result


def audit_legacy(root=ROOT, fetch=None):
    root = Path(root)
    directory = root / "legacy_preservation" / "samples"
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    source_entries = manifest["records"]
    index = {entry["archive_path"]: entry["source_blob_sha"] for entry in source_entries}
    names = sorted(p for p in directory.glob("*.json") if CODE.fullmatch(p.name))
    if len(names) != len(index) or any("legacy_preservation/samples/" + p.name not in index for p in names):
        raise ValueError("manifest_and_legacy_coverage_mismatch")
    fetch = fetch or result_from_pinned_repo
    overall = blank_group()
    by_day, by_venue = defaultdict(blank_group), defaultdict(blank_group)
    excluded, evaluated = Counter(), []
    for path in names:
        key = path.stem
        try:
            if path.is_symlink() or path.stat().st_size > 35000:
                raise ValueError("unsafe_legacy_archive")
            raw = path.read_bytes()
            if blob_sha(raw) != index["legacy_preservation/samples/" + path.name]:
                raise ValueError("legacy_archive_changed_since_original")
            pred = json.loads(raw)
            deadline, modes = checked_legacy_forecast(pred, key)
            official, result_blob = fetch(key)
            winning = checked_result(official, key, deadline)
        except (OSError, ValueError, TypeError, KeyError, urllib.error.URLError) as exc:
            excluded[str(exc)[:95] or type(exc).__name__] += 1
            continue
        add_record(overall, modes, winning)
        add_record(by_day[key[:8]], modes, winning)
        add_record(by_venue[key[9:11]], modes, winning)
        evaluated.append({"race_key": key, "forecast_blob": blob_sha(raw),
                          "result_blob": result_blob, "winning_ticket": winning,
                          "legacy_mode_sizes": {m: len(v) for m,v in modes.items()},
                          "winning_rank": {m: (v.index(winning) + 1 if winning in v else None)
                                            for m,v in modes.items()}})
    return {"status": "legacy_v133_frozen_historical_only",
            "registered_before_results_independently_proven": False,
            "model": "legacy_V127_V133_3_10_10_12_15_18",
            "source_repository": OLD_REPO,
            "source_result_commit": PINNED_OLD_RESULTS_COMMIT,
            "all_preserved_archive_count": len(names),
            "excluded": dict(excluded),
            "overall": summarize(overall),
            "by_day": {k: summarize(v) for k,v in sorted(by_day.items())},
            "by_venue": {k: summarize(v) for k,v in sorted(by_venue.items())},
            "race_audit": evaluated}


def audit_clean_versioned(root=ROOT):
    """Compute all saved V1/V2 archive matches; no cross-version pooling."""
    root = Path(root)
    forecasts = root / "four_mode_forecasts"
    results = root / "confirmed_results"
    versions = defaultdict(blank_group)
    rejected = Counter()
    total_files = 0
    result_count = 0
    for file in sorted(forecasts.glob("*.json")):
        if not NEW_CODE.fullmatch(file.stem):
            continue
        total_files += 1
        if not (results / file.name).is_file():
            rejected["no_confirmed_result_file"] += 1
            continue
        result_count += 1
        try:
            if file.is_symlink() or file.stat().st_size > 40000:
                raise ValueError("unsafe_forecast")
            prediction = json.loads(file.read_text(encoding="utf-8"))
            version = prediction["model_version"]
            if (prediction.get("race_code") != file.stem
                    or not re.fullmatch(r"CLEAN_FOUR_MODES_V[0-9]+_[A-Z0-9_]+", version)):
                raise ValueError("not_a_clean_four_mode_archive")
            paired = compare_race(file.stem, root)
            if paired.get("status") != "historical_comparison_only":
                rejected[paired.get("status", "not_comparable")] += 1
                continue
            winning = paired["winning_ticket"]
            modes = {m: [x["combo"] for x in prediction["modes"][m]["tickets"]] for m in MODES}
            for picks in modes.values():
                if len(picks) != len(set(picks)):
                    raise ValueError("duplicate_frozen_ticket")
            add_record(versions[version], modes, winning)
        except (OSError, ValueError, TypeError, KeyError) as exc:
            rejected["invalid_record"] += 1
    return {"status": "clean_v1_v2_archived_comparison_only",
            "all_forecasts_scanned": total_files,
            "with_result_file": result_count,
            "excluded": dict(rejected),
            "by_model_version": {k: summarize(v) for k,v in sorted(versions.items())},
            "cannot_directly_compare_to_legacy_due_to_different_dates": True}


def report(root=ROOT, fetch=None):
    root = Path(root)
    v133 = sorted((root / "v133_policy_forecasts").glob("*.json"))
    final = {
        "schema": "BOAT_EDGE_MASS_HISTORICAL_AUDIT_V1",
        "formal": False, "accuracy_improvement_proven": False,
        "outcome_leakage_prohibited": True,
        "live_model_modified": False,
        "current_model": "V127_V133_BALANCE12_HOLE15_18_20_REFERENCE_V2",
        "current_model_frozen_research_receipts": len(v133),
        "current_policy_historical_v133_not_mislabeled_as_new_points": True,
        "historical_legacy": audit_legacy(root, fetch),
        "archived_clean_baseline": audit_clean_versioned(root),
        "caveats": [
            "Old V133 3/10/10/12-15-18 is not current 3/10/12/15-18-20.",
            "Historical archive timestamps and original Git first receipt not independently attested.",
            "CLEAN V1/V2 national-rate models are separate, not scenario forecasts.",
            "Different dates and budgets cannot establish scenario-model superiority.",
            "No retroactive predictions from post-race cards, and no 300+300 prospective pass.",
            "ROI unavailable without trustworthy race-aligned actual stakes and payout records."
        ]}
    return final


def main():
    out = report()
    dest = Path("artifacts") / "historical-v133-mass-audit.json"
    dest.parent.mkdir(exist_ok=True)
    dest.write_text(json.dumps(out, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    compact = {k:v for k,v in out.items() if k != "historical_legacy" and k != "archived_clean_baseline"}
    compact["historical_legacy"] = {
        k:v for k,v in out["historical_legacy"].items() if k not in ("by_day", "by_venue", "race_audit")}
    compact["archived_clean_baseline"] = out["archived_clean_baseline"]
    print("HISTORICAL_MASS_AUDIT=" + json.dumps(compact, ensure_ascii=False, sort_keys=True), flush=True)
    # Missing 79-result coverage is NOT considered a valid completed mass audit.
    if out["historical_legacy"]["overall"]["evaluated"] < 50:
        raise ValueError("insufficient_verified_old_v133_results_for_mass_audit")


if __name__ == "__main__":
    main()
