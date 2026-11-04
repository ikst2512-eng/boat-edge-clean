"""Fail-closed, read-only scoring of three CI-sourced frozen historical race rosters.

No forecasting, candidate selection, production mutation or remote-first-seen claims.
The membership roster is frozen in-repository; source outputs may still be unproven
prospectively. A changed artifact, a missing result, or a bad hash cannot turn into
a miss or an accuracy percentage.
"""
import hashlib
import json
import re
from pathlib import Path

from four_mode_historical_cohort import ROOT, summarize_group
from four_mode_research_batch import MODES

MANIFEST = ROOT / "research" / "locked_four_mode_cohorts_20261105.json"
PROOF = {
    "prior_120": (120, "08be2da77dff8ddff58bdde66c1f6872db6a7fed7096f3ac0bc12c4cd6a0796f",
                  41487274739, 13162392806, "training_codes"),
    "holdout_240": (240, "eb6b066002d8e149a50fd0e5ccc3f42bc9bf394e5c452416edde0aed99bc0ad1",
                    41487274739, 13162392806, "heldout_codes"),
    "rolling_120": (120, "f983f3e31a39e3766ce95b932cce513894cfb4e62f17fd3d359d2ae3237e2e77",
                    41888211981, 13350929305, "cohort_codes"),
}
TOPS = ("top1", "top3", "top5", "top10")


def roster_digest(codes):
    return hashlib.sha256(("\n".join(codes) + "\n").encode("ascii")).hexdigest()


def load_locked_manifest(path=MANIFEST):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or not 100 <= path.stat().st_size <= 40000:
        raise ValueError("manifest_unavailable_or_untrusted")
    raw = path.read_bytes()
    try:
        data = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise ValueError("invalid_manifest_json") from exc
    if (not isinstance(data, dict)
            or data.get("schema") != "FOUR_MODE_RETROSPECTIVE_COHORT_LOCK_V1"
            or data.get("formal") is not False
            or data.get("prospective_validation") is not False
            or data.get("remote_first_seen_verified") is not False
            or not isinstance(data.get("cohorts"), dict)
            or set(data["cohorts"]) != set(PROOF)):
        raise ValueError("invalid_manifest_contract")

    sets = {}
    for name, (n, digest, run, artifact, field) in PROOF.items():
        row = data["cohorts"][name]
        if not isinstance(row, dict):
            raise ValueError("invalid_roster_row")
        codes = row.get("codes")
        if (type(codes) is not list or len(codes) != n
                or any(type(c) is not str or re.fullmatch(r"20[0-9]{10}", c) is None
                       for c in codes)
                or codes != sorted(set(codes))):
            raise ValueError("invalid_roster_membership")
        if (row.get("expected_n") != n or row.get("sha256") != digest
                or row.get("actions_run_id") != run
                or row.get("artifact_id") != artifact
                or row.get("source_field") != field
                or roster_digest(codes) != digest):
            raise ValueError("roster_provenance_or_hash_mismatch")
        sets[name] = set(codes)
    overlaps = {
        "prior_holdout": len(sets["prior_120"] & sets["holdout_240"]),
        "rolling_holdout": len(sets["rolling_120"] & sets["holdout_240"]),
        "prior_rolling": len(sets["prior_120"] & sets["rolling_120"]),
    }
    if overlaps != {"prior_holdout": 0, "rolling_holdout": 0, "prior_rolling": 86}:
        raise ValueError("unexpected_cohort_overlap")
    if data.get("expected_overlaps") != overlaps:
        raise ValueError("manifest_overlap_claim_mismatch")
    return data, hashlib.sha256(raw).hexdigest()


def run(root=ROOT, manifest_path=MANIFEST):
    data, manifest_sha = load_locked_manifest(manifest_path)
    root = Path(root)
    cohorts = {}
    complete = True
    for name, info in data["cohorts"].items():
        codes = info["codes"]
        report = summarize_group(codes, root, include_per_race=True)
        observed = report["historical_comparable"]
        if observed > len(codes):
            raise ValueError("denominator_exceeds_frozen_roster")
        ok = observed == len(codes)
        complete &= ok
        present = {r["race_code"] for r in report["per_race"]}
        if len(present) != observed or not present.issubset(set(codes)):
            raise ValueError("evaluated_race_id_mismatch")
        # No accuracy rate on an incomplete cohort. A missing result is NOT a loss.
        rates = ({
            mode: {top: round(100 * report["topn_hits"][mode][top] / len(codes), 2)
                   for top in TOPS}
            for mode in MODES} if ok else None)
        cohorts[name] = {
            "status": "historical_research_only" if ok else "incomplete_historical_evidence",
            "formal": False, "remote_first_seen_verified": False,
            "expected_race_codes_sha256": info["sha256"],
            "source_actions_run_id": info["actions_run_id"],
            "source_artifact_id": info["artifact_id"],
            "requested": len(codes), "comparable": observed,
            "unavailable_codes": sorted(set(codes) - present),
            "topn_hits_on_comparable_only": report["topn_hits"],
            "historical_topn_pct": rates,
            "pairwise_topn": report["pairwise_topn"] if ok else None,
        }
    return {
        "schema": "FOUR_MODE_LOCKED_HISTORICAL_AUDIT_V1",
        "status": "historical_complete" if complete else "incomplete_historical_evidence",
        "formal": False, "prospective_validation": False,
        "remote_first_seen_verified": False, "model_improvement_proven": False,
        "production_forecast_changed": False,
        "manifest_sha256": manifest_sha,
        "cohort_membership_frozen_in_git": True,
        "overlaps": data["expected_overlaps"],
        "cohorts": cohorts,
        "warning": ("Every group is retrospective, even when its race IDs do not overlap "
                    "another group. No independent pre-T-12 remote-first-seen proof.")
    }


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="pinned_four_mode_cohort_report.json")
    args = parser.parse_args()
    result = run()
    # Emit an inspectable artifact even when paired evidence is incomplete.
    Path(args.output).write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")
    print("PINNED_FOUR_MODE_COHORT=" + json.dumps({
        "status": result["status"], "manifest_sha256": result["manifest_sha256"],
        "overlaps": result["overlaps"],
        "cohorts": {name: {
            "status": row["status"], "requested": row["requested"],
            "comparable": row["comparable"], "missing": len(row["unavailable_codes"]),
            "topn": row["topn_hits_on_comparable_only"] if row["historical_topn_pct"] is not None else None}
            for name, row in result["cohorts"].items()}
    }, ensure_ascii=False, sort_keys=True))
    return 0 if result["status"] == "historical_complete" else 2


if __name__ == "__main__":
    raise SystemExit(main())
