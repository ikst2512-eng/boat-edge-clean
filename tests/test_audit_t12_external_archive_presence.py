"""No live network: strict inventory read-only verification with mock GitHub API."""
import unittest
from urllib.error import HTTPError
from urllib.parse import urlsplit, parse_qs

from scripts.audit_t12_external_archive_presence import inventory

REPO = "ikst2512-eng/boat-edge-clean"
SHA = "d0ed89f146dff117021c2bc042b20259d6715515"
ROOT = "external_three_t12"
DAY = "20261108"
RACE = "202611080309"


def dirs(parent, names):
    return [{"name": name, "path": parent + "/" + name, "type": "dir"}
            for name in names]


def fake(*, days=None, races=None, branch=None, bad_path=None, error=None):
    days = ["20261103"] if days is None else days
    races = [] if races is None else races
    branch = {"commit": {"sha": SHA}} if branch is None else branch

    def fetch(url):
        parsed = urlsplit(url)
        path = parsed.path
        if not path.startswith("/repos/" + REPO + "/"):
            raise AssertionError("wrong repository")
        endpoint = path.split("/repos/" + REPO + "/", 1)[1]
        if error == endpoint:
            raise HTTPError(url, 403, "Forbidden", {}, None)
        if endpoint == "branches/research-t12-external-evidence":
            return branch
        if parse_qs(parsed.query) != {"ref": [SHA]}:
            raise AssertionError("not pinned to immutable branch commit")
        if endpoint == "contents/" + ROOT:
            return dirs(ROOT, days)
        if endpoint == "contents/" + ROOT + "/" + DAY:
            if bad_path:
                return dirs(ROOT + "/wrong-day", races)
            return dirs(ROOT + "/" + DAY, races)
        raise AssertionError("unexpected GitHub endpoint " + endpoint)
    return fetch


class IndependentThreeSourceArchivePresence(unittest.TestCase):
    def test_nov8_missing_day_is_not_success_or_certificate(self):
        result = inventory(REPO, DAY, fetch=fake())
        self.assertEqual(result["status"],
                         "no_persisted_three_original_day_directory")
        self.assertFalse(result["day_directory_present"])
        self.assertEqual(result["race_directory_count"], 0)
        self.assertEqual(result["existing_day_directories"], ["20261103"])
        self.assertEqual(result["evidence_branch_commit_sha"], SHA)
        for flag in ("originals_replayed",
                     "github_initial_remote_receipt_verified",
                     "full_t12_source_certified", "formal", "t12_eligible",
                     "accuracy_scoring_allowed"):
            self.assertIs(result[flag], False)

    def test_directory_only_is_unverified_not_formal(self):
        result = inventory(REPO, DAY, fetch=fake(days=["20261103", DAY],
                                                  races=[RACE, "202611081409"]))
        self.assertEqual(result["status"], "persisted_race_directories_unverified")
        self.assertEqual(result["race_directories"],
                         ["202611080309", "202611081409"])
        self.assertEqual(result["race_directory_count"], 2)
        self.assertFalse(result["full_t12_source_certified"])
        self.assertFalse(result["accuracy_scoring_allowed"])

    def test_existing_day_with_zero_races_still_not_certified(self):
        result = inventory(REPO, DAY, fetch=fake(days=[DAY]))
        self.assertTrue(result["day_directory_present"])
        self.assertEqual(result["race_directory_count"], 0)
        self.assertFalse(result["formal"])

    def test_403_is_never_treated_as_missing_day_or_success(self):
        for endpoint in ("branches/research-t12-external-evidence",
                         "contents/external_three_t12",
                         "contents/external_three_t12/" + DAY):
            with self.subTest(endpoint=endpoint), self.assertRaises(HTTPError):
                inventory(REPO, DAY,
                          fetch=fake(days=[DAY], races=[RACE], error=endpoint))

    def test_invalid_branch_identity_fails(self):
        for bad in ({}, {"commit": {"sha": "not-a-commit"}},
                    {"commit": {"sha": None}}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                inventory(REPO, DAY, fetch=fake(branch=bad))

    def test_invalid_directory_layout_fails(self):
        with self.assertRaises(ValueError):
            inventory(REPO, DAY, fetch=fake(days=["not-a-day"]))
        with self.assertRaises(ValueError):
            inventory(REPO, DAY, fetch=fake(days=[DAY], races=[RACE],
                                           bad_path=True))
        with self.assertRaises(ValueError):
            inventory(REPO, DAY,
                      fetch=fake(days=[DAY], races=["202611090309"]))
        with self.assertRaises(ValueError):
            inventory(REPO, DAY, fetch=fake(days=[DAY], races=[RACE, RACE]))

    def test_absent_token_without_injected_fetch_rejected(self):
        with self.assertRaisesRegex(ValueError, "token"):
            inventory(REPO, DAY, None)

    def test_invalid_repositories_and_calendar_days_rejected(self):
        for repo, day in ((REPO, "20261301"), (REPO, "20260230"),
                          (REPO, "20261108/../20261103"),
                          ("invalid", DAY), ("bad/repo/extra", DAY)):
            with self.subTest(repo=repo, day=day), self.assertRaises(ValueError):
                inventory(repo, day, fetch=fake())

    def test_day_check_without_matching_subfolder_does_not_guess_count(self):
        # Presence inventory deliberately never infers a race count from
        # scheduling logs, prior dates, or similar named directories.
        result = inventory(REPO, DAY,
                           fetch=fake(days=["20261103", "20261107"]))
        self.assertEqual(result["race_directory_count"], 0)
        self.assertFalse(result["day_directory_present"])

    def test_truthy_model_claims_are_not_consulted(self):
        result = inventory(REPO, DAY,
                           fetch=fake(days=[DAY], races=[RACE]))
        self.assertFalse(result["originals_replayed"])
        self.assertFalse(result["github_initial_remote_receipt_verified"])
        self.assertFalse(result["formal"])


if __name__ == "__main__":
    unittest.main()
