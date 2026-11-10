"""Read-only Nov10 first-file-added GitHub server witness for frozen forecasts.

Source originals and immutable forecast blobs MUST first be replayed by the
existing Nov10 source-vs-forecast audit. An Actions created_at is an upper
bound for remote commit existence, NOT its exact first remote acceptance.
"""
import argparse
import json
import os
import re
from pathlib import Path
from urllib.request import Request, urlopen
from datetime import timedelta
from scripts.audit_t12_source_forecast_join import stamp

REPO = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")
HEX = re.compile(r"[0-9a-f]{40}\Z")
DAY = "20261110"
CODES = ("202611101202", "202611102211")
REF = "c4d39245cbc96b6c680585a68c3b9adf6ddeb921"
WITNESSES = {
    "clean": ("d5ec88ccd7bfec3b8c6844bbc0a3b47e61375eda",
              42714563095, "prospective_predictions", "workflow_dispatch"),
    "v2_four_mode": ("e79a99e5180892330fd3ce0b745893d3c6515ab8",
                     42657194420, "four_mode_forecasts", "workflow_run"),
}


def verify(replay, commits, runs, repo):
    if not isinstance(repo, str) or not REPO.fullmatch(repo):
        raise ValueError("invalid bound repository")
    if (not isinstance(replay, dict)
            or replay.get("schema") != "T12_PINNED_SCHEDULED_PAIR_FROZEN_REPLAY_V1"
            or replay.get("source_run_id") != 42769768447
            or replay.get("source_artifact_id") != 13740574410
            or replay.get("source_original_zip_sha256_from_metadata") !=
                "cdfdeae53222a5b7852ba5cf5b6b44080247ec074c8d3dbaf53c4a32fe9706dd"
            or replay.get("pinned_forecast_ref") != REF
            or replay.get("day_jst") != DAY
            or replay.get("source_originals_individually_replayed") is not True
            or replay.get("original_zip_directly_rehashed_inside_ci") is not False
            or replay.get("complete_two_original_races") != 1
            or replay.get("original_source_candidate_races") != 2
            or replay.get("matched_immutable_forecasts") != 4
            or replay.get("forecasts_generated_after_originals") != 0
            or replay.get("same_race_complete_official_three_originals") != 0
            or replay.get("verified_model_original_byte_consumption") != 0
            or replay.get("verified_first_forecast_remote_acceptances") != 0
            or replay.get("new_formal_certifications") != 0
            or replay.get("formal_accuracy_denominator") is not None
            or replay.get("formal") is not False):
        raise ValueError("Nov10 official source/forecast replay not provenance-pinned")
    rows = replay.get("race_rows")
    if (not isinstance(rows, list) or len(rows) != 2
            or sorted(x.get("race_code") if isinstance(x, dict) else ""
                      for x in rows) != list(CODES)
            or not isinstance(commits, dict) or set(commits) != set(WITNESSES)
            or not isinstance(runs, dict) or set(runs) != set(WITNESSES)):
        raise ValueError("mixed race or incomplete remote witness")
    witnesses = {}
    for mode, (sha, run_id, folder, event) in WITNESSES.items():
        commit, run = commits[mode], runs[mode]
        if (not isinstance(commit, dict) or commit.get("sha") != sha
                or not isinstance(commit.get("parents"), list)
                or len(commit["parents"]) != 1
                or not HEX.fullmatch(str(commit["parents"][0].get("sha")))
                or not isinstance(commit.get("files"), list)):
            raise ValueError("wrong introduced-file commit or parent")
        if (not isinstance(run, dict) or run.get("id") != run_id
                or run.get("head_sha") != sha
                or run.get("head_branch") != "main"
                or run.get("event") != event
                or (run.get("repository") or {}).get("full_name") != repo
                or (run.get("head_repository") or {}).get("full_name") != repo
                or run.get("status") not in ("queued", "in_progress", "completed")):
            raise ValueError("server witness did not observe exact Git commit")
        # A failed job still witnesses remote commit existence; not a prediction.
        seen = stamp(run.get("created_at"), offset=timedelta(0))
        authored = stamp(commit.get("commit", {}).get("committer", {}).get("date"),
                         offset=timedelta(0))
        if seen < authored:
            raise ValueError("server observation predates commit self clock")
        witnesses[mode] = (sha, run_id, folder, commit["files"], seen)
    results = []
    for row in sorted(rows, key=lambda x: x["race_code"]):
        race = row["race_code"]
        if (row.get("formal") is not False
                or row.get("official_racelist_original_replayed") is not False
                or row.get("first_forecast_git_remote_acceptance_proven") is not False
                or row.get("model_consumption_proven") is not False):
            raise ValueError("false claimed official or forecast proof")
        deadline = stamp(row.get("official_t12_cutoff_jst"), offset=timedelta(hours=9))
        source = stamp(row.get("last_original_source_received_jst"),
                       offset=timedelta(hours=9))
        if (deadline.strftime("%Y%m%d") != DAY
                or source.strftime("%Y%m%d") != DAY or source > deadline):
            raise ValueError("mixed or impossible original source clocks")
        frozen = row.get("frozen_forecasts")
        if not isinstance(frozen, dict) or set(frozen) != set(WITNESSES):
            raise ValueError("missing same race and same mode forecasts")
        mode_rows = {}
        for mode, (sha, run_id, folder, files, remote_time) in witnesses.items():
            file = frozen[mode]
            if (not isinstance(file, dict) or file.get("formal") is not False
                    or file.get("generated_after_pair_sources") is not False
                    or file.get("first_forecast_git_remote_acceptance_verified") is not False
                    or file.get("actual_model_official_original_bytes_consumption_verified") is not False
                    or not isinstance(file.get("forecast_git_blob_sha1"), str)
                    or not HEX.fullmatch(file["forecast_git_blob_sha1"])):
                raise ValueError("source-consuming frozen forecast not independently proven")
            path = folder + "/" + race + ".json"
            additions = [x for x in files if isinstance(x, dict)
                         and x.get("filename") == path]
            if (len(additions) != 1 or additions[0].get("status") != "added"
                    or additions[0].get("sha") != file["forecast_git_blob_sha1"]):
                raise ValueError("Git commit added-file bytes mismatch pinned forecast")
            generated = stamp(file.get("generated_at_jst"),
                              offset=timedelta(hours=9))
            if (generated.strftime("%Y%m%d") != DAY
                    or generated > remote_time or remote_time >= source
                    or remote_time >= deadline):
                raise ValueError("server does not establish pre-source forecast existence")
            mode_rows[mode] = {
                "added_path": path, "added_git_commit": sha,
                "exact_file_git_blob_sha1_matched": True,
                "independent_github_run_id": run_id,
                "github_remote_existed_no_later_utc": remote_time.isoformat(),
                "existing_blob_predates_official_source": True,
                "first_remote_acceptance_instant_proven": False,
                "actual_original_byte_model_consumption_proven": False,
                "formal": False,
            }
        results.append({"race_code": race,
                        "official_t12_cutoff_jst": deadline.isoformat(),
                        "last_source_received_jst": source.isoformat(),
                        "forecasts": mode_rows, "formal": False})
    return {
        "schema": "T12_NOV10_REMOTE_ADDED_BLOB_WITNESS_V1",
        "source_races": 2, "immutable_forecast_blobs_witnessed": 4,
        "remote_commit_existed_before_official_sources": 4,
        "exact_first_remote_git_acceptance_instants_verified": 0,
        "forecasts_proven_to_consume_official_originals": 0,
        "full_three_source_forecasts_verified": 0,
        "new_formal_certifications": 0, "formal_accuracy_denominator": None,
        "race_rows": results, "formal": False, "accuracy_scoring_allowed": False,
        "scope_note": ("A commit added status is parent-relative; a Github Actions "
                       "created_at is the remote existence upper bound, NOT the first "
                       "Git acceptance instant or proof of original source consumption."),
    }


def github_get(repo, token, route):
    if not isinstance(repo, str) or not REPO.fullmatch(repo) or not token:
        raise ValueError("invalid read-only GitHub credentials")
    request = Request("https://api.github.com/repos/" + repo + "/" + route,
                      headers={"Authorization": "Bearer " + token,
                               "Accept": "application/vnd.github+json",
                               "X-GitHub-Api-Version": "2022-11-28",
                               "Cache-Control": "no-cache"})
    with urlopen(request, timeout=25) as response:
        if response.status != 200:
            raise ValueError("independent Github server evidence unavailable")
        return json.load(response)


def audit(repo, token, existing, fetch=github_get):
    if not isinstance(repo, str) or not REPO.fullmatch(repo) or not token:
        raise ValueError("invalid GitHub read-only evidence credentials")
    commits = {mode: fetch(repo, token, "commits/" + spec[0])
               for mode, spec in WITNESSES.items()}
    runs = {mode: fetch(repo, token, "actions/runs/" + str(spec[1]))
            for mode, spec in WITNESSES.items()}
    return verify(existing, commits, runs, repo)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--replayed-nov10", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    prior = json.loads(Path(args.replayed_nov10).read_text(encoding="utf-8"))
    result = audit(args.repo, os.environ.get("GITHUB_TOKEN"), prior)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8")
    print("T12_REMOTE_ADDED_BLOB_WITNESS=" + json.dumps(
        {k: v for k, v in result.items() if k != "race_rows"},
        ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
