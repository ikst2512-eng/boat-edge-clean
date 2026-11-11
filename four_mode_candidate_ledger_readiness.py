"""Read-only GitHub evidence-branch inventory of ALL-MODE prospective candidates.

The ledger's Git tree and exact original blobs show durable candidate presence
and bounded observation, never the *first* remote acceptance, official T-12
source completeness, or a valid prospective performance denominator.
No candidate generation, result reads, production writes or new schedule.
"""
import argparse
import base64
import hashlib
import json
import os
import re
import urllib.request
from collections import Counter

REPO = "ikst2512-eng/boat-edge-clean"
BRANCH = "v2-third-rate-evidence-ledger"
TREE_SHA = re.compile(r"[0-9a-f]{40}\Z")
ENTRY = re.compile(
    r"(four_mode_all|four_mode_all_observation)/(20[0-9]{6})/"
    r"run-([1-9][0-9]*)-attempt-([1-9][0-9]*)\.json\Z"
)
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
PREFIXES = ("four_mode_all/", "four_mode_all_observation/")
SCHEMA = "FOUR_MODE_ALL_SHADOW_AFTER_PUSH_RESEARCH_V1"
NOTE_SCHEMA = "FOUR_MODE_ALL_REMOTE_LEDGER_V1"


def git_blob_sha(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def review(tree, get_blob):
    """Only one immutable Git tree; reject partial or mismatched evidence."""
    if (type(tree) is not dict or tree.get("truncated") is not False
            or not isinstance(tree.get("sha"), str)
            or not TREE_SHA.fullmatch(tree["sha"])
            or type(tree.get("tree")) is not list):
        raise ValueError("incomplete_or_unpinned_evidence_tree")
    items = {}
    for entry in tree["tree"]:
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
            raise ValueError("invalid_tree_entry")
        path = entry["path"]
        if not path.startswith(PREFIXES):
            continue
        if entry.get("type") == "tree":
            if (not re.fullmatch(r"(four_mode_all|four_mode_all_observation)/20[0-9]{6}", path)
                    or entry.get("mode") != "040000"):
                raise ValueError("unsafe_candidate_ledger_directory")
            continue
        match = ENTRY.fullmatch(path)
        if (match is None or entry.get("type") != "blob"
                or entry.get("mode") != "100644"
                or not isinstance(entry.get("sha"), str)
                or not TREE_SHA.fullmatch(entry["sha"])
                or type(entry.get("size")) is not int
                or not 0 < entry["size"] <= 2_000_000
                or path in items):
            raise ValueError("unsafe_candidate_ledger_tree_entry")
        kind, day, run, attempt = match.groups()
        items[path] = (kind, day, run, attempt, entry["sha"], entry["size"])

    by_key = {}
    for path, item in items.items():
        kind, day, run, attempt, sha, length = item
        key = (day, run, attempt)
        by_key.setdefault(key, {})
        if kind in by_key[key]:
            raise ValueError("duplicate_candidate_run_identity")
        raw = get_blob(sha)
        if type(raw) is not bytes or len(raw) != length or git_blob_sha(raw) != sha:
            raise ValueError("candidate_ledger_git_blob_mismatch")
        try:
            obj = json.loads(raw)
        except (ValueError, UnicodeError) as exc:
            raise ValueError("invalid_candidate_ledger_json") from exc
        if type(obj) is not dict or obj.get("formal") is not False:
            raise ValueError("forged_formal_candidate_evidence")
        if kind == "four_mode_all":
            if (obj.get("schema") != SCHEMA
                    or obj.get("candidate_first_remote_receipt_verified") is not False
                    or obj.get("production_forecast_changed") is not False
                    or type(obj.get("frozen_count")) is not int
                    or obj["frozen_count"] < 1
                    or type(obj.get("records")) is not list
                    or sum(isinstance(x, dict) and x.get("status") ==
                           "frozen_local_before_T_minus_12_research_only"
                           for x in obj["records"]) != obj["frozen_count"]):
                raise ValueError("invalid_or_forged_candidate_original")
        else:
            if (obj.get("schema") != NOTE_SCHEMA
                    or obj.get("candidate_first_remote_receipt_verified") is not False
                    or obj.get("candidate_github_server_observation_not_first_receipt") is not True
                    or obj.get("branch") != BRANCH
                    or obj.get("path") !=
                       f"four_mode_all/{day}/run-{run}-attempt-{attempt}.json"
                    or str(obj.get("capture_run_id")) != run
                    or str(obj.get("capture_run_attempt")) != attempt
                    or not isinstance(obj.get("candidate_sha256"), str)
                    or not SHA256.fullmatch(obj["candidate_sha256"])
                    or type(obj.get("observed_before_t_minus_12")) is not int
                    or type(obj.get("observed_late_or_ambiguous")) is not int
                    or min(obj["observed_before_t_minus_12"],
                           obj["observed_late_or_ambiguous"]) < 0):
                raise ValueError("invalid_or_forged_candidate_observation")
        by_key[key][kind] = (obj, hashlib.sha256(raw).hexdigest())

    status = Counter()
    candidates = []
    for (day, run, attempt), pair in sorted(by_key.items()):
        original = pair.get("four_mode_all")
        observed = pair.get("four_mode_all_observation")
        if observed is not None and original is None:
            raise ValueError("observation_note_without_candidate_original")
        if original is None:
            continue
        obj, digest = original
        if observed:
            note = observed[0]
            if (note["candidate_sha256"] != digest
                    or note["locally_frozen_count"] != obj["frozen_count"]
                    or note["observed_before_t_minus_12"] +
                       note["observed_late_or_ambiguous"] != obj["frozen_count"]):
                raise ValueError("candidate_and_observation_digest_or_count_mismatch")
            status["matching_observation_notes"] += 1
            status["github_observed_before_t12_not_first_receipt"] += note[
                "observed_before_t_minus_12"]
            candidate_status = "durable_candidate_and_bounded_observation_only"
        else:
            status["candidate_without_observation_note"] += 1
            candidate_status = "candidate_original_only"
        candidates.append({
            "day": day, "capture_run_id": run, "capture_run_attempt": attempt,
            "frozen_count": obj["frozen_count"], "candidate_sha256": digest,
            "status": candidate_status,
            "independent_first_remote_receipt_verified": False,
            "formal": False,
        })
    return {
        "schema": "FOUR_MODE_ALL_CANDIDATE_DURABLE_REMOTE_READINESS_V1",
        "branch": BRANCH, "pinned_evidence_tree_sha": tree["sha"],
        "status": ("reference_only_candidates_present" if candidates
                   else "no_durable_all_mode_candidates_in_inspected_branch"),
        "durable_candidate_run_artifacts": len(candidates),
        "durable_candidate_records": sum(x["frozen_count"] for x in candidates),
        "matching_observation_notes": status["matching_observation_notes"],
        "candidate_without_observation_note": status["candidate_without_observation_note"],
        "github_observed_before_t12_not_first_receipt":
            status["github_observed_before_t12_not_first_receipt"],
        "candidates": candidates,
        "official_three_originals_verified": False,
        "independent_first_remote_candidate_receipt_verified": False,
        "complete_run_attempt_inventory_verified": False,
        "future_paired_races_admitted": 0,
        "formal": False, "model_improvement_proven": False,
        "model_promotion_allowed": False,
        "warning": "Read-only single evidence branch; absence here does not prove absence "
                   "of all Actions artifacts. GitHub after-the-fact observation "
                   "is NOT independently attested first remote receipt.",
    }


def fetch_live(token):
    if not token:
        raise ValueError("missing_read_only_github_token")
    base = f"https://api.github.com/repos/{REPO}"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": "Bearer " + token,
        "X-GitHub-Api-Version": "2022-11-28",
        "Cache-Control": "no-cache",
        "User-Agent": "four-mode-candidate-readonly-inventory",
    }

    def get(url, limit):
        request = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(request, timeout=30) as response:
            if response.status != 200:
                raise ValueError("github_api_not_200")
            payload = response.read(limit + 1)
            if len(payload) > limit:
                raise ValueError("oversized_github_evidence")
        return json.loads(payload)

    tree = get(base + "/git/trees/" + BRANCH + "?recursive=1", 12_000_000)
    def blob(sha):
        if not TREE_SHA.fullmatch(sha):
            raise ValueError("invalid_git_blob_id")
        payload = get(base + "/git/blobs/" + sha, 3_000_000)
        if (type(payload) is not dict or payload.get("sha") != sha
                or payload.get("encoding") != "base64"
                or type(payload.get("content")) is not str):
            raise ValueError("invalid_git_blob_api_response")
        try:
            return base64.b64decode(payload["content"], validate=False)
        except ValueError as exc:
            raise ValueError("invalid_git_blob_base64") from exc
    return review(tree, blob)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output")
    args = p.parse_args()
    result = fetch_live(os.environ.get("GH_TOKEN"))
    printed = json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(printed)
    print("FOUR_MODE_ALL_REMOTE_CANDIDATE_READINESS=" + json.dumps(
        {k: v for k, v in result.items() if k != "candidates"},
        ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
