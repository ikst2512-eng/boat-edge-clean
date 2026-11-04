"""Result-last cross-check of archived four-mode hole shadow and remote observation.

Inputs must originate from ORIGINAL same-job GitHub Actions evidence, not
regenerated predictions. Even a passing check does NOT certify formal
first-receipt, complete run inventory, official six-racer cards or returns.
"""
import hashlib
import json
import re
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

from four_mode_frozen_diagnostic import compare_race
from hole_upper_rank_pair_protection import propose
from forward_hole_rank3_protocol import validate as validate_protocol

ROOT = Path(__file__).resolve().parent
SHA = re.compile(r"[0-9a-f]{40}\Z")
HEX = re.compile(r"[0-9a-f]{64}\Z")
TICKET = re.compile(r"[1-6]-[1-6]-[1-6]\Z")
CODE = re.compile(r"20[0-9]{6}(?:0[1-9]|1[0-9]|2[0-4])(?:0[1-9]|1[0-2])\Z")
JST = timedelta(hours=9)
TOPS = (1, 3, 5, 10)


def _invalid(reason, code):
    return {"race_code": code, "status": "excluded_unverified_evidence",
            "reason": reason, "formal": False, "scorable": False,
            "independent_first_receipt_verified": False}


def _timestamp(value, offset):
    if type(value) is not str:
        raise ValueError("timestamp_missing")
    dt = datetime.fromisoformat(value)
    if dt.utcoffset() != offset:
        raise ValueError("timestamp_timezone_invalid")
    return dt


def _tickets(value):
    if (type(value) is not list or len(value) < 10 or len(value) > 120):
        raise ValueError("invalid_original_ticket_list")
    seq = [v.get("combo") if type(v) is dict else None for v in value]
    if (len(seq) != len(set(seq))
            or any(type(t) is not str or TICKET.fullmatch(t) is None
                   or len(set(t.split("-"))) != 3 for t in seq)):
        raise ValueError("invalid_original_ticket_list")
    return seq


def inspect_race(code, root, publication, hole_shadow, observation, *,
                 git=None, result_reader=compare_race, score_outcome=True):
    """Fail closed and only read independently confirmed outcome LAST.

    This checks consistency of captured GitHub observations, not the
    authenticity of a downloaded ZIP or exhaustive Action-run inventory.
    """
    if type(score_outcome) is not bool:
        raise ValueError("invalid_scoring_gate")
    if type(code) is not str or CODE.fullmatch(code) is None:
        raise ValueError("invalid_race_code")
    if not ("20261105" <= code[:8] <= "20261231"):
        return _invalid("outside_predeclared_study_window", code)
    if any(type(item) is not dict for item in (publication, hole_shadow, observation)):
        return _invalid("missing_original_capture_evidence", code)
    validate_protocol()
    root = Path(root)
    sha = publication.get("commit_sha")
    count = publication.get("added_forecasts")
    if (publication.get("outcome") != "pushed_to_main"
            or type(sha) is not str or SHA.fullmatch(sha) is None
            or type(count) is not int or not 1 <= count <= 500):
        return _invalid("untrusted_publication", code)
    if (hole_shadow.get("schema") != "HOLE_SHADOW_PUBLISHED_SAME_JOB_V1"
            or hole_shadow.get("status") != "research_only_after_confirmed_push"
            or hole_shadow.get("formal") is not False
            or hole_shadow.get("independent_first_receipt_verified") is not False
            or hole_shadow.get("publication_commit_sha") != sha
            or hole_shadow.get("published_new_count") != count
            or type(hole_shadow.get("records")) is not list
            or len(hole_shadow["records"]) != count):
        return _invalid("untrusted_shadow_roster", code)
    if (observation.get("schema") != "FOUR_MODE_GITHUB_REMOTE_OBSERVATION_V1"
            or observation.get("status") != "remote_observation_audited_nonformal"
            or observation.get("formal") is not False
            or observation.get("independent_first_remote_receipt_verified") is not False
            or observation.get("github_server_observation_not_first_receipt") is not True
            or observation.get("publication_commit_sha") != sha
            or observation.get("publication_count") != count
            or type(observation.get("records")) is not list
            or len(observation["records"]) != count):
        return _invalid("untrusted_observation_roster", code)
    shadows, observed = hole_shadow["records"], observation["records"]
    if any(type(x) is not dict for x in shadows + observed):
        return _invalid("malformed_evidence_row", code)
    shadow_codes = [x.get("race_code") for x in shadows]
    observed_codes = [x.get("race_code") for x in observed]
    if (len(set(shadow_codes)) != count or len(set(observed_codes)) != count
            or set(shadow_codes) != set(observed_codes) or code not in shadow_codes):
        return _invalid("publication_evidence_race_roster_mismatch", code)
    shadow = next(x for x in shadows if x["race_code"] == code)
    remote = next(x for x in observed if x["race_code"] == code)
    if shadow.get("status") != "shadow_frozen_unverified":
        return _invalid("shadow_not_frozen", code)
    if remote.get("status") != "github_server_observed_before_t_minus_12":
        return _invalid("no_predeadline_github_server_observation", code)
    if (remote.get("first_add_commit") != sha
            or remote.get("first_add_blob_matches_remote") is not True
            or remote.get("independent_first_remote_receipt_verified") is not False
            or type(remote.get("original_sha256")) is not str
            or HEX.fullmatch(remote["original_sha256"]) is None):
        return _invalid("github_observation_not_bound_to_original", code)
    # Verify exact first-added Git bytes, the added path roster, and current
    # checkout equality before considering post-race results.
    git = git or (lambda args: subprocess.check_output(["git", *args], cwd=root, timeout=30))
    path = "four_mode_forecasts/" + code + ".json"
    try:
        roster = git(["diff-tree", "--no-commit-id", "--name-only",
                      "--diff-filter=A", "-r", sha, "--", "four_mode_forecasts/"])
        if type(roster) is not bytes:
            raise ValueError("unreadable_additions")
        names = roster.decode("utf-8").splitlines()
        if (len(names) != count or len(set(names)) != count or path not in names
                or sorted(names) != sorted("four_mode_forecasts/" + x + ".json"
                                          for x in shadow_codes)):
            raise ValueError("first_add_roster_not_matched")
        # A Draft-branch or unattached SHA must never masquerade as an
        # immutable original already on production main. Require ancestry
        # against the caller's freshly fetched remote main ref.
        ancestor = git(["merge-base", "--is-ancestor", sha,
                        "refs/remotes/origin/main"])
        if type(ancestor) is not bytes or ancestor:
            raise ValueError("untrusted_main_ancestry")
        original = git(["show", sha + ":" + path])
        if type(original) is not bytes or len(original) > 30000:
            raise ValueError("invalid_git_original")
        local = root / path
        if local.is_symlink() or not local.is_file() or local.read_bytes() != original:
            raise ValueError("changed_or_missing_original")
        original_hash = hashlib.sha256(original).hexdigest()
        if (remote["original_sha256"] != original_hash
                or shadow.get("source_sha256") != original_hash):
            raise ValueError("original_sha_mismatch")
        archive = json.loads(original)
        if (type(archive) is not dict or archive.get("race_code") != code
                or archive.get("schema") != "CLEAN_FOUR_MODES_PREDEADLINE_V1"
                or archive.get("validated") is not False
                or archive.get("model_version") !=
                "CLEAN_FOUR_MODES_V2_PROVISIONAL_UNCALIBRATED"):
            raise ValueError("invalid_original_four_mode_archive")
        cutoff = _timestamp(archive["deadline_jst"], JST) - timedelta(minutes=12)
        if cutoff.strftime("%Y%m%d") != code[:8]:
            raise ValueError("deadline_wrong_day")
        generated = _timestamp(archive["generated_at_jst"], JST)
        title = _timestamp(archive["source_title_received_jst"], JST)
        cards = _timestamp(archive["source_cards_received_jst"], JST)
        freeze = _timestamp(shadow["local_freeze_at_jst"], JST)
        frozen_cutoff = _timestamp(shadow["t_minus_12_jst"], JST)
        observed_at = _timestamp(remote["github_api_server_date_utc"], timedelta(0))
        observed_cutoff = _timestamp(remote["deadline_minus_12_jst"], JST)
        if (frozen_cutoff != cutoff or observed_cutoff != cutoff
                or not max(title, cards) <= generated <= freeze < cutoff
                or not observed_at < cutoff
                or shadow.get("deadline_jst") != archive["deadline_jst"]):
            raise ValueError("inconsistent_t_minus_12_timeline")
        modes = archive["modes"]
        if type(modes) is not dict or set(modes) != {
                "hole", "hit", "balance", "narrow"}:
            raise ValueError("invalid_four_mode_set")
        baseline = _tickets(modes["hole"]["tickets"])[:10]
        donor = _tickets(modes["hit"]["tickets"])
        # Recompute the predeclared deterministic selector without looking
        # at the result, only as an immutable saved-candidate consistency test.
        expected = propose(baseline, donor, 3)
        if (shadow.get("candidate_algorithm") !=
                "hole_upper_rank_pair_protection.propose:hit_rank3:v1"
                or shadow.get("baseline") != baseline
                or shadow.get("shadow") != expected
                or len(expected) != 10 or len(set(expected)) != 10):
            raise ValueError("saved_shadow_not_predeclared_candidate")
    except (OSError, ValueError, TypeError, KeyError, AttributeError,
            UnicodeError, subprocess.SubprocessError) as exc:
        return _invalid("source_or_freeze_evidence_mismatch_" + type(exc).__name__, code)

    # Pre-result enrollment must not inspect the confirmed finish, payout or
    # any other after-race data. The roster must be frozen independently.
    if not score_outcome:
        return {
            "race_code": code,
            "status": "pre_result_evidence_consistent_research_only",
            "deadline_jst": archive["deadline_jst"],
            "source_git_commit_sha": sha,
            "source_sha256": original_hash,
            "github_server_observed_at_utc": remote["github_api_server_date_utc"],
            "baseline_top10": baseline,
            "candidate_top10": expected,
            "formal": False,
            "first_remote_receipt_verified": False,
            "capture_run_inventory_verified": False,
            "original_actions_artifact_origin_authenticated": False,
            "result_accessed": False,
            "warning": "Only pre-result field consistency; not real independently attested original or complete capture inventory.",
        }

    # All original/source/shadow/remote evidence checked BEFORE result access.
    result = result_reader(code, root)
    if type(result) is not dict or result.get("status") == "result_unavailable":
        return {"race_code": code, "status": "pending_independent_result",
                "formal": False, "scorable": False,
                "independent_first_receipt_verified": False}
    if (result.get("status") != "historical_comparison_only"
            or result.get("formal") is not False
            or result.get("remote_first_seen_verified") is not False
            or result.get("race_code") != code):
        return _invalid("untrusted_confirmed_result", code)
    winner = result.get("winning_ticket")
    if (type(winner) is not str or TICKET.fullmatch(winner) is None
            or len(set(winner.split("-"))) != 3):
        return _invalid("untrusted_result_ticket", code)
    scores = {}
    for k in TOPS:
        key = "top" + str(k)
        old = winner in baseline[:k]
        new = winner in expected[:k]
        scores[key] = {"baseline": old, "candidate": new,
                       "gained": new and not old, "lost": old and not new}
    return {"race_code": code,
            "status": "matched_saved_shadow_and_remote_observation_research_only",
            "formal": False, "scorable": True,
            "independent_first_receipt_verified": False,
            "complete_capture_run_inventory_verified": False,
            "official_six_boat_beforeinfo_verified": False,
            "source_git_commit_sha": sha,
            "source_sha256": original_hash, "winning_ticket": winner,
            "candidate_was_recomputed_only_for_integrity": True,
            "topn": scores,
            "warning": ("Evidence fields are internally consistent, not "
                        "independently authenticated first receipt or "
                        "officially certified prospective accuracy.")}


if __name__ == "__main__":
    raise SystemExit("This is a library gate. Provide original same-job evidence through reviewed tooling.")
