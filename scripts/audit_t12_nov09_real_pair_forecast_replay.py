"""Independent Nov-09 official pair vs pinned immutable CLEAN/V2 forecast replay.

For this one bounded cohort, an authenticated Actions v4 artifact is extracted
and every source original SHA, URL, race, cutoff and completeness independently
replayed by audit_t12_extracted_artifact_replay. Forecast Git blobs are fetched
at a pinned immutable main commit. Their existence/committer clocks are NOT
independent first-remote-acceptance proofs. Never authorize formal scoring.
"""
import argparse
import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path

from scripts.audit_t12_extracted_artifact_replay import artifact_metadata, replay_extracted
from scripts.audit_t12_archived_pair_forecast_replay import frozen_remote

RUN_ID = 42567310743
ARTIFACT_ID = 13652131213
ZIP_SHA256 = "99f02ff306307dd945f27c225e18ff8341be2832232b7dd0f2751e1d8935f451"
FORECAST_REF = "a77c905893d7412dc99e68cabd2091bd579cc9bf"
DAY = "20261109"
RACES = ("202611091110", "202611091710")
HEX = re.compile(r"[a-f0-9]{64}\Z")
REPO = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")
JST = timedelta(hours=9)


def _stamp(raw, code):
    if not isinstance(raw, str):
        raise ValueError("source/forecast timestamp missing")
    try:
        moment = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError("invalid timestamp") from exc
    if moment.utcoffset() != JST or moment.strftime("%Y%m%d") != code[:8]:
        raise ValueError("non-JST or cross-day evidence")
    return moment


def reconcile(originals, *, get_frozen):
    """Only replayed source report permitted; never infer missing original files."""
    if (not isinstance(originals, dict)
            or originals.get("run_id") != RUN_ID
            or originals.get("day_jst") != DAY
            or originals.get("original_actions_artifact_sha256") != ZIP_SHA256
            or originals.get("github_artifact_digest_metadata_matches") is not True
            or originals.get("extracted_original_source_bytes_replayed") is not True
            or originals.get("github_original_zip_digest_verified_by_local_hash") is not False
            or originals.get("official_racelist_originals_verified") != 0
            or originals.get("full_t12_source_certified") is not False
            or originals.get("formal") is not False
            or originals.get("status") != "source_pairs_independently_replayed_nonformal"
            or originals.get("candidate_count") != 2
            or originals.get("two_original_complete_race_count") != 2):
        raise ValueError("Nov9 two-source original replay not independently verified")
    race_rows = originals.get("race_rows")
    if (not isinstance(race_rows, list) or len(race_rows) != 2
            or sorted(r.get("race_code") if isinstance(r, dict) else ""
                      for r in race_rows) != list(RACES)):
        raise ValueError("Nov9 archived race roster mismatch")
    result_rows = []
    for row in sorted(race_rows, key=lambda r: r["race_code"]):
        code = row["race_code"]
        if (row.get("formal") is not False
                or row.get("two_originals_complete_by_t12") is not True
                or row.get("official_odds_120_verified") is not True
                or row.get("exhibition_time_observed_boats") != 6
                or row.get("start_exhibition_six_valid_rows") is not True
                or row.get("official_racelist_original_replayed") is not False):
            raise ValueError("Nov9 stored original component proof incomplete")
        cutoff = _stamp(row.get("official_t12_cutoff_jst"), code)
        before = _stamp(row.get("beforeinfo_received_jst"), code)
        last = _stamp(row.get("last_source_received_jst"), code)
        if last < before or last > cutoff:
            raise ValueError("official source received after cutoff or reversed")
        modes = {}
        for label, folder in (
                ("clean", "prospective_predictions"),
                ("v2_four_mode", "four_mode_forecasts")):
            path = f"{folder}/{code}.json"
            frozen, pinned = get_frozen(path)
            if not isinstance(frozen, dict) or frozen.get("race_code") != code:
                raise ValueError("wrong frozen forecast identity")
            ts = [frozen[k] for k in ("generated_at", "generated_at_jst")
                  if frozen.get(k) is not None]
            if len(ts) != 1:
                raise ValueError("missing or ambiguous original generation time")
            generated = _stamp(ts[0], code)
            if (not isinstance(pinned, dict)
                    or pinned.get("pinned_remote_commit") != FORECAST_REF
                    or not isinstance(pinned.get("remote_sha256"), str)
                    or HEX.fullmatch(pinned["remote_sha256"]) is None
                    or not isinstance(pinned.get("remote_git_blob_sha1"), str)
                    or re.fullmatch(r"[a-f0-9]{40}",
                                    pinned["remote_git_blob_sha1"]) is None):
                raise ValueError("forecast Git original bytes not verified")
            modes[label] = {
                "generation_jst": generated.isoformat(),
                "last_official_source_minus_generation_seconds":
                    round((last-generated).total_seconds(), 3),
                "generated_strictly_after_official_pair": generated > last,
                "generated_by_official_t12": generated <= cutoff,
                "declared_input_source_kind": frozen.get("input_source_kind"),
                "declared_beforeinfo": frozen.get("beforeinfo"),
                "pinned_main_commit": FORECAST_REF,
                "remote_git_blob_sha1": pinned["remote_git_blob_sha1"],
                "remote_sha256": pinned["remote_sha256"],
                "independent_actual_model_original_consumption_verified": False,
                "first_git_remote_receipt_verified": False,
                "formal": False,
            }
        result_rows.append({
            "race_code": code,
            "official_beforeinfo_received_jst": before.isoformat(),
            "official_latest_original_received_jst": last.isoformat(),
            "official_t12_cutoff_jst": cutoff.isoformat(),
            "official_pair_originals_replayed_complete": True,
            "racelist_official_original_present": False,
            "forecasts": modes,
            "missing_requirements": [
                "third_official_racelist_original_not_replayed",
                "no_new_post_official_original_forecast",
                "model_input_official_original_consumption_unverified",
                "independent_first_git_remote_receipt_unverified",
                "final_race_entry_not_independently_verified",
            ],
            "formal": False,
            "accuracy_scoring_allowed": False,
        })
    return {
        "schema": "T12_NOV09_REAL_OFFICIAL_PAIR_VS_FROZEN_FORECAST_V1",
        "source_run_id": RUN_ID,
        "source_artifact_id": ARTIFACT_ID,
        "github_original_artifact_digest_from_metadata": ZIP_SHA256,
        "github_original_zip_digest_locally_rehashed_by_ci": False,
        "extracted_official_source_originals_replayed": True,
        "forecast_pinned_main_sha": FORECAST_REF,
        "two_original_complete_races": len(result_rows),
        "matched_pinned_forecasts": sum(len(x["forecasts"]) for x in result_rows),
        "matched_forecasts_generated_after_sources": sum(
            bool(m["generated_strictly_after_official_pair"])
            for r in result_rows for m in r["forecasts"].values()),
        "race_rows": result_rows,
        "three_official_original_races": 0,
        "new_formal_certifications": 0,
        "formal_accuracy_denominator": None,
        "independent_first_remote_receipt_verified": False,
        "independent_model_input_consumption_verified": False,
        "final_race_entry_verified": False,
        "formal": False,
        "t12_eligible": False,
        "accuracy_scoring_allowed": False,
    }


def run(repo, token, root, *, fetch_metadata=artifact_metadata,
        replay_source=replay_extracted, get_forecast=frozen_remote):
    if (not isinstance(repo, str) or REPO.fullmatch(repo) is None
            or not isinstance(token, str) or not token):
        raise ValueError("authenticated GitHub read access required")
    metadata = fetch_metadata(repo, token, ARTIFACT_ID)
    source = replay_source(
        Path(root), run_id=RUN_ID, artifact_id=ARTIFACT_ID,
        digest=ZIP_SHA256, metadata=metadata)
    return reconcile(
        source, get_frozen=lambda path: get_forecast(repo, token, FORECAST_REF, path))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repo", required=True)
    p.add_argument("--extracted-root", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()
    result = run(args.repo, os.environ.get("GITHUB_TOKEN"),
                 args.extracted_root)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                      encoding="utf-8")
    print("T12_NOV09_REAL_SOURCE_FROZEN_REPLAY=" + json.dumps(
        {k: v for k, v in result.items() if k != "race_rows"},
        ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
