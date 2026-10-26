"""Research-only, fail-closed offline audit. Never reads formal Fresh datasets.

Input manifests are assessor-produced attestations, NOT proof on their own. The auditor
does not fetch or infer official results, commit-push times, or provenance.
"""
import argparse
import hashlib
import json
import math
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

REQUIRED_EVIDENCE = ("receipt_verified", "model_verified", "inputs_verified", "result_verified")
TOPS = (1, 3, 5, 10)


def timestamp(s):
    d = datetime.fromisoformat(s)
    if d.tzinfo is None or d.utcoffset() is None:
        raise ValueError("timezone required")
    return d


def wilson(hits, n, z=1.959963984540054):
    if n == 0:
        return None
    p = hits / n
    a = 1 + z*z/n
    mid = (p + z*z/(2*n))/a
    delta = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))/a
    return [max(0, mid-delta), min(1, mid+delta)]


def audit(snapshot_dir, attestations, results, approved_attestations_sha256=None):
    """Returns separate counts for exclusions and a defensible matched sample.

    Each manifest must be verified by a separate reviewer against independent
    timestamped receipts, immutable first-added blob, model and source hashes,
    and official results. Self-asserted booleans MUST NOT be used as substitutes.
    """
    # A reviewer must pin the exact serialized evidence manifest hash independently.
    # No pin means no score, even when all self-declared verified flags are true.
    manifest_digest = hashlib.sha256(
        json.dumps(attestations, ensure_ascii=False, sort_keys=True,
                   separators=(",", ":")).encode()
    ).hexdigest()
    authorized = (
        isinstance(approved_attestations_sha256, str)
        and approved_attestations_sha256 == manifest_digest
    )
    by_code = {}
    for item in attestations:
        code = item["race_code"]
        if code in by_code:
            raise ValueError("duplicate attestation: " + code)
        by_code[code] = item
    outcomes = {}
    for item in results:
        code = item["race_code"]
        if code in outcomes:
            raise ValueError("duplicate result: " + code)
        outcomes[code] = item

    exclusions = Counter()
    matched = []
    seen = set()
    for path in sorted(Path(snapshot_dir).glob("*.json")):
        code = path.stem
        seen.add(code)
        try:
            raw = path.read_bytes()
            obj = json.loads(raw)
            if obj.get("race_code") != code or len(code) != 12 or not code.isdigit():
                raise ValueError("race identity mismatch")
            if obj.get("status") != "research" or obj.get("validated") is not False:
                raise ValueError("not a research forecast")
            picks = obj["predictions"]
            if len(picks) != 10 or len(set(picks)) != 10 or any(
                len(p.split("-")) != 3 or set(p.split("-")) - set("123456") or
                len(set(p.split("-"))) != 3 for p in picks
            ):
                raise ValueError("invalid picks")
            att = by_code.get(code)
            if not att:
                exclusions["missing_independent_attestation"] += 1
                continue
            if not authorized:
                exclusions["missing_independent_manifest_approval"] += 1
                continue
            if not all(att.get(k) is True for k in REQUIRED_EVIDENCE):
                exclusions["unverified_provenance_or_result"] += 1
                continue
            if not all(isinstance(att.get(k), str) and att[k] for k in
                       ("receipt_id", "model_git_sha", "model_file_sha256", "input_sha256")):
                exclusions["missing_provenance_identifiers"] += 1
                continue
            # Historical records lacking pre-race model/input fingerprints cannot
            # acquire that provenance through a later attestation.
            if not obj.get("model_git_sha") or not obj.get("input_sha256"):
                exclusions["missing_frozen_model_or_input_hash"] += 1
                continue
            if (obj["model_git_sha"] != att["model_git_sha"] or
                    obj["input_sha256"] != att["input_sha256"] or
                    obj.get("model_source_sha256") != att["model_file_sha256"]):
                exclusions["provenance_mismatch"] += 1
                continue
            # Both original CSV byte digests must be frozen, not merely a
            # composite string supplied after the result is known.
            if (obj.get("input_hash_scope") != "source_csv_byte_hashes_ordered_title_cards"
                    or not all(isinstance(obj.get(k), str) and len(obj[k]) == 64
                               and all(c in "0123456789abcdef" for c in obj[k])
                               for k in ("source_title_sha256", "source_cards_sha256"))):
                exclusions["missing_source_byte_hashes"] += 1
                continue
            combined = hashlib.sha256(
                (obj["source_title_sha256"] + ":" + obj["source_cards_sha256"]).encode("ascii")
            ).hexdigest()
            if combined != obj["input_sha256"]:
                exclusions["input_hash_inconsistent"] += 1
                continue
            if hashlib.sha256(raw).hexdigest() != att.get("snapshot_sha256"):
                exclusions["snapshot_hash_mismatch"] += 1
                continue
            if timestamp(att["first_seen_at"]) > timestamp(obj["cutoff_jst"]):
                exclusions["receipt_after_cutoff"] += 1
                continue
            if timestamp(obj["generated_at"]) > timestamp(obj["cutoff_jst"]) or any(
                timestamp(obj[k]) > timestamp(obj["cutoff_jst"]) for k in
                ("source_title_received_jst", "source_cards_received_jst")
            ):
                exclusions["late_generation_or_input"] += 1
                continue
            if (timestamp(att["first_seen_at"]) < timestamp(obj["generated_at"]) or
                    any(timestamp(obj[k]) > timestamp(obj["generated_at"]) for k in
                        ("source_title_received_jst", "source_cards_received_jst"))):
                exclusions["impossible_evidence_chronology"] += 1
                continue
            deadline = timestamp(att["official_deadline_at"])
            if timestamp(obj["cutoff_jst"]) != deadline-timedelta(minutes=12):
                exclusions["deadline_disagreement"] += 1
                continue
            res = outcomes.get(code)
            if not res or res.get("verified") is not True:
                exclusions["no_verified_result"] += 1
                continue
            # A result flag alone is insufficient. Keep source provenance and
            # a post-deadline verification timestamp on the research side.
            if not isinstance(res.get("result_source_id"), str) or not res["result_source_id"]:
                exclusions["missing_result_provenance"] += 1
                continue
            if not isinstance(res.get("result_confirmed_at"), str) or not res["result_confirmed_at"]:
                exclusions["missing_result_confirmation_time"] += 1
                continue
            if timestamp(res["result_confirmed_at"]) < deadline:
                exclusions["result_confirmed_before_deadline"] += 1
                continue
            outcome = res.get("trifecta")
            if outcome not in ("-".join([str(i), str(j), str(k)])
                               for i in range(1,7) for j in range(1,7)
                               for k in range(1,7) if len({i,j,k}) == 3):
                exclusions["invalid_result"] += 1
                continue
            matched.append({"race_code":code, "outcome":outcome,
                            "rank": picks.index(outcome)+1 if outcome in picks else None})
        except (ValueError, KeyError, TypeError, UnicodeError):
            exclusions["malformed_snapshot_or_manifest"] += 1
    for code in by_code.keys()-seen:
        exclusions["attestation_without_snapshot"] += 1
    n = len(matched)
    return {"scope":"research_only", "snapshot_count":len(seen),
            "valid_count":n, "excluded_snapshot_count":len(seen)-n,
            "exclusion_reasons":dict(sorted(exclusions.items())),
            "metrics":{f"top{k}":{"hits":sum(r["rank"] is not None and r["rank"]<=k for r in matched),
                    "rate":sum(r["rank"] is not None and r["rank"]<=k for r in matched)/n if n else None,
                    "wilson95":wilson(sum(r["rank"] is not None and r["rank"]<=k for r in matched),n)}
                    for k in TOPS},
            "matched_races":matched,
            "warning":"Attestations require independent verification; fixture outcomes are not actual performance."}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--snapshots",default="research_snapshots")
    parser.add_argument("--attestations",required=True)
    parser.add_argument("--results",required=True)
    parser.add_argument("--output")
    parser.add_argument(
        "--approved-attestations-sha256",
        help="Independently approved digest of canonical JSON attestations"
    )
    args=parser.parse_args()
    report=audit(args.snapshots,json.loads(Path(args.attestations).read_text()),
                 json.loads(Path(args.results).read_text()), args.approved_attestations_sha256)
    content=json.dumps(report,ensure_ascii=False,indent=2)
    if args.output:
        Path(args.output).write_text(content+"\n")
    else:
        print(content)


if __name__=="__main__":
    main()
