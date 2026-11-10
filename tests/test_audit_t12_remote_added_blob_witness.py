"""Fail-closed independent remote-existence upper bound; no first-push claim."""
import unittest
from copy import deepcopy
from scripts.audit_t12_remote_added_blob_witness import (
    verify, audit, WITNESSES, CODES, REF
)

REPO = "ikst2512-eng/boat-edge-clean"
BLOBS = {
    "clean": ("288edca70f45331d0db6b5c46a078748e973575d",
              "7d9c78fef48c3a6851daba3c09fe03e424ddf36c"),
    "v2_four_mode": ("d7801a878c4f2d1fd296f2d21c38906e92df0efb",
                     "f6f20088220f2c42d785f4b4eada20eef5d930cd")
}

def saved():
    records = []
    for i, race in enumerate(CODES):
        items = {mode: {
            "generated_at_jst": ("2026-11-10T07:44:29+09:00" if mode == "clean"
                                 else "2026-11-10T01:39:35+09:00"),
            "forecast_git_blob_sha1": blobs[i],
            "generated_after_pair_sources": False,
            "first_forecast_git_remote_acceptance_verified": False,
            "actual_model_official_original_bytes_consumption_verified": False,
            "formal": False,
        } for mode, blobs in BLOBS.items()}
        records.append({
            "race_code": race,
            "official_t12_cutoff_jst": ("2026-11-10T15:40:00+09:00" if i == 0
                                        else "2026-11-10T15:46:00+09:00"),
            "last_original_source_received_jst": (
                "2026-11-10T15:38:04.755388+09:00" if i == 0
                else "2026-11-10T15:38:23.339785+09:00"),
            "official_racelist_original_replayed": False,
            "first_forecast_git_remote_acceptance_proven": False,
            "model_consumption_proven": False,
            "frozen_forecasts": items, "formal": False,
        })
    return {
        "schema": "T12_PINNED_SCHEDULED_PAIR_FROZEN_REPLAY_V1",
        "source_run_id": 42769768447, "source_artifact_id": 13740574410,
        "source_original_zip_sha256_from_metadata":
            "cdfdeae53222a5b7852ba5cf5b6b44080247ec074c8d3dbaf53c4a32fe9706dd",
        "pinned_forecast_ref": REF, "day_jst": "20261110",
        "source_originals_individually_replayed": True,
        "original_zip_directly_rehashed_inside_ci": False,
        "complete_two_original_races": 1, "original_source_candidate_races": 2,
        "matched_immutable_forecasts": 4,
        "forecasts_generated_after_originals": 0,
        "same_race_complete_official_three_originals": 0,
        "verified_model_original_byte_consumption": 0,
        "verified_first_forecast_remote_acceptances": 0,
        "new_formal_certifications": 0, "formal_accuracy_denominator": None,
        "race_rows": records, "formal": False,
    }

def evidence():
    commits, runs = {}, {}
    for mode, (sha, run_id, folder, event) in WITNESSES.items():
        commits[mode] = {
            "sha": sha, "parents": [{"sha": "a"*40}],
            "commit": {"committer": {"date": (
                "2026-11-09T22:44:30Z" if mode == "clean"
                else "2026-11-09T16:39:36Z")}},
            "files": [{"filename": folder + "/" + race + ".json",
                       "sha": BLOBS[mode][i], "status": "added"}
                      for i, race in enumerate(CODES)]
        }
        runs[mode] = {
            "id": run_id, "head_sha": sha, "head_branch": "main",
            "event": event, "repository": {"full_name": REPO},
            "head_repository": {"full_name": REPO},
            "created_at": ("2026-11-09T22:44:34Z" if mode == "clean"
                           else "2026-11-09T16:40:45Z"),
            "status": "completed",
            "conclusion": "failure" if mode == "clean" else "success",
        }
    return commits, runs

def check(s=None, c=None, r=None):
    a,b = evidence()
    return verify(s if s is not None else saved(),
                  c if c is not None else a,
                  r if r is not None else b, REPO)


class RemoteWitnessNotFirstRemoteReceipt(unittest.TestCase):
    def test_two_races_four_blobs_positive_remote_exists_not_first_accept(self):
        x = check()
        self.assertEqual(x["immutable_forecast_blobs_witnessed"], 4)
        self.assertEqual(x["remote_commit_existed_before_official_sources"], 4)
        self.assertEqual(x["exact_first_remote_git_acceptance_instants_verified"], 0)
        self.assertEqual(x["new_formal_certifications"], 0)
        self.assertFalse(x["accuracy_scoring_allowed"])
        self.assertIsNone(x["formal_accuracy_denominator"])

    def test_failed_action_still_witnesses_commit_existence_not_forecast(self):
        x = check()
        for row in x["race_rows"]:
            a = row["forecasts"]["clean"]
            self.assertTrue(a["existing_blob_predates_official_source"])
            self.assertFalse(a["first_remote_acceptance_instant_proven"])
            self.assertFalse(a["actual_original_byte_model_consumption_proven"])

    def test_false_run_sha_event_repository_and_clock_rejected(self):
        for key, value in (
            ("head_sha", "0"*40), ("event", "schedule"),
            ("id", 1), ("head_branch", "other"),
            ("repository", {"full_name": "other/repo"}),
            ("created_at", "2026-11-10T06:38:25Z"),
            ("created_at", "2026-11-09T22:44:29Z")):
            a, b = evidence()
            b["clean"][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                check(c=a, r=b)

    def test_edited_or_cross_race_git_blob_cannot_be_borrowed(self):
        for field, value in (("status", "modified"), ("sha", "0"*40),
                             ("filename", "prospective_predictions/202611102211.json")):
            a, b = evidence()
            a["clean"]["files"][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                check(c=a, r=b)

    def test_missing_parent_file_and_unpinned_commit_rejected(self):
        a, b = evidence()
        a["clean"]["parents"] = []
        with self.assertRaises(ValueError):
            check(c=a, r=b)
        a, b = evidence()
        a["clean"]["sha"] = "0"*40
        with self.assertRaises(ValueError):
            check(c=a, r=b)

    def test_unreplayed_or_self_proclaimed_formal_rejected(self):
        for field, value in (("source_originals_individually_replayed", False),
                             ("matched_immutable_forecasts", 2),
                             ("formal", True),
                             ("verified_first_forecast_remote_acceptances", 1)):
            s = saved()
            s[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                check(s=s)

    def test_frozen_generated_after_remotely_existing_blob_rejected(self):
        s = saved()
        s["race_rows"][0]["frozen_forecasts"]["clean"]["generated_at_jst"] = (
            "2026-11-10T15:38:10+09:00")
        with self.assertRaises(ValueError):
            check(s=s)

    def test_exact_authenticated_endpoints_only_injectable(self):
        visited = []
        def fake(repo, token, route):
            self.assertEqual(repo, REPO)
            self.assertEqual(token, "mock")
            visited.append(route)
            a, b = evidence()
            return (next(x for x in a.values() if x["sha"] == route[8:])
                    if route.startswith("commits/") else
                    next(x for x in b.values() if str(x["id"]) == route[13:]))
        x = audit(REPO, "mock", saved(), fetch=fake)
        self.assertEqual(len(visited), 4)
        self.assertEqual(x["immutable_forecast_blobs_witnessed"], 4)


if __name__ == "__main__":
    unittest.main()
