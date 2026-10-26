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
import subprocess
from scripts.verify_research_git_first_add import verify_first_add

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


def audit(snapshot_dir, attestations, results, approved_attestations_sha256=None, git_repo=None, trusted_ref='refs/heads/main'):
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
            if path.is_symlink() or not path.is_file() or path.stat().st_size > 20_000:
                exclusions["unsafe_snapshot_file"] += 1
                continue
            raw = path.read_bytes()
            obj = json.loads(raw)
            if (obj.get("race_code") != code or len(code) != 12
                    or not code.isascii() or not code.isdigit()):
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
            # Git blob SHA-1 is independently reproducible from exact snapshot
            # bytes. The assessor must separately verify commit membership and
            # remote receipt time; this calculation alone proves neither.
            first_commit = att.get("first_added_commit_sha")
            blob = att.get("first_added_blob_sha")
            if (not isinstance(first_commit, str) or len(first_commit) != 40
                    or any(c not in "0123456789abcdef" for c in first_commit)
                    or not isinstance(blob, str) or len(blob) != 40):
                exclusions["missing_first_added_git_evidence"] += 1
                continue
            git_blob = hashlib.sha1(
                b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
            ).hexdigest()
            if git_blob != blob:
                exclusions["first_added_blob_mismatch"] += 1
                continue
            # Commit ID and blob digest alone do not prove membership or first
            # introduction. These checks must be performed independently before
            # a score can be promoted to a validated research result.
            if (att.get("first_commit_membership_verified") is not True or
                    att.get("first_commit_introduction_verified") is not True or
                    att.get("remote_receipt_verified") is not True):
                exclusions["unverified_first_commit_or_remote_receipt"] += 1
                continue
            if git_repo is None:
                exclusions["git_history_not_verified"] += 1
                continue
            git_proof = verify_first_add(git_repo, code, first_commit, trusted_ref)
            if (git_proof.get("verified") is not True or
                    git_proof.get("first_added_blob_sha") != blob or
                    git_proof.get("snapshot_sha256") != att["snapshot_sha256"]):
                exclusions["git_first_add_verification_failed"] += 1
                continue
            # Verify the model source against the claimed commit, not only a
            # digest duplicated inside the assessor-provided manifest.
            model_commit = obj["model_git_sha"]
            if (not isinstance(model_commit, str) or len(model_commit) != 40 or
                    any(c not in "0123456789abcdef" for c in model_commit)):
                exclusions["invalid_model_commit_identifier"] += 1
                continue
            try:
                subprocess.check_call(
                    ["git", "-C", str(git_repo), "merge-base", "--is-ancestor",
                     model_commit, first_commit],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10,
                )
                committed_model = subprocess.check_output(
                    ["git", "-C", str(git_repo), "show",
                     model_commit + ":research_model.py"],
                    stderr=subprocess.DEVNULL, timeout=10,
                )
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
                exclusions["model_git_source_unavailable"] += 1
                continue
            if hashlib.sha256(committed_model).hexdigest() != obj["model_source_sha256"]:
                exclusions["model_git_source_mismatch"] += 1
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
            if res.get("race_code") != code or att.get("race_code") != code:
                exclusions["race_identity_disagreement"] += 1
                continue
            if (not isinstance(att.get("result_source_id"), str) or
                    att["result_source_id"] != res["result_source_id"] or
                    att.get("confirmed_trifecta") != res.get("trifecta")):
                exclusions["result_attestation_mismatch"] += 1
                continue
            outcome = res.get("trifecta")
            if outcome not in ("-".join([str(i), str(j), str(k)])
                               for i in range(1,7) for j in range(1,7)
                               for k in range(1,7) if len({i,j,k}) == 3):
                exclusions["invalid_result"] += 1
                continue
            matched.append({"race_code":code, "outcome":outcome,
                            "rank": picks.index(outcome)+1 if outcome in picks else None})
        except (ValueError, KeyError, TypeError, UnicodeError, OSError, OverflowError):
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
    parser.add_argument("--git-repo", help="Local checked-out repository for independent Git ancestry validation")
    parser.add_argument("--trusted-ref", default="refs/heads/main")
    parser.add_argument(
        "--approved-attestations-sha256",
        help="Independently approved digest of canonical JSON attestations"
    )
    args=parser.parse_args()
    report=audit(args.snapshots,json.loads(Path(args.attestations).read_text()),
                 json.loads(Path(args.results).read_text()), args.approved_attestations_sha256,
                 git_repo=args.git_repo, trusted_ref=args.trusted_ref)
    content=json.dumps(report,ensure_ascii=False,indent=2)
    if args.output:
        Path(args.output).write_text(content+"\n")
    else:
        print(content)


if __name__=="__main__":
    main()
