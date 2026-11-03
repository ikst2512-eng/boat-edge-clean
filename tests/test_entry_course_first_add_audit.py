import unittest
from datetime import datetime
from urllib.parse import urlparse,parse_qs
from entry_course_first_add_audit import first_add_for_path,audit_first_add

PATH="t12_baselines/20261103/202611030708.json"
CUTOFF="2026-11-03T18:21:00+09:00"
REPO="ikst2512-eng/boat-edge-clean"
COMMIT="a"*40


def fetch(path, *, event="added", at="2026-11-03T09:00:00Z", count=1):
    if path.startswith(f"repos/{REPO}/commits?"):
        page=int(parse_qs(urlparse(path).query)["page"][0])
        if page==1:
            return [{"sha":COMMIT}]*count
        return []
    if path==f"repos/{REPO}/commits/{COMMIT}":
        return {"sha":COMMIT,"files":[{"filename":PATH,"status":event}],
                "commit":{"committer":{"date":at}}}
    raise AssertionError(path)


class FirstAddTests(unittest.TestCase):
    def test_first_add_commit_before_cutoff_is_not_server_proof(self):
        item=first_add_for_path(PATH,cutoff_at=CUTOFF,
            fetch=fetch,repository=REPO)
        self.assertEqual(item["first_add_sha"],COMMIT)
        self.assertTrue(item["commit_timestamp_before_cutoff"])
        self.assertFalse(item["independent_server_first_seen_verified"])
        self.assertEqual(item["status"],"first_add_commit_observed")
    def test_after_cutoff_is_negative_signal(self):
        result=first_add_for_path(PATH,cutoff_at=CUTOFF,
            fetch=lambda path:fetch(path,at="2026-11-03T09:30:00Z"),
            repository=REPO)
        self.assertFalse(result["commit_timestamp_before_cutoff"])
    def test_earliest_change_not_added_is_not_claimed_first_add(self):
        result=first_add_for_path(PATH,cutoff_at=CUTOFF,
            fetch=lambda path:fetch(path,event="modified"),repository=REPO)
        self.assertEqual(result["status"],"earliest_change_not_addition")
    def test_missing_history_is_not_zero_timestamp(self):
        result=first_add_for_path(PATH,cutoff_at=CUTOFF,
            fetch=lambda route:[] if "commits?" in route else self.fail("no commit"),
            repository=REPO)
        self.assertEqual(result["status"],"history_missing")
    def test_invalid_sha_fails_closed(self):
        with self.assertRaisesRegex(ValueError,"history_sha_invalid"):
            first_add_for_path(PATH,cutoff_at=CUTOFF,
                fetch=lambda route:[{"sha":"notsha"}],
                repository=REPO)
    def test_bounded_truncated_pagination_is_explicit(self):
        result=first_add_for_path(PATH,cutoff_at=CUTOFF,
            fetch=lambda route:[{"sha":COMMIT}]*100,repository=REPO)
        self.assertEqual(result["status"],"history_pagination_incomplete")
    def test_error_is_per_path_not_fake_success(self):
        records=[{"path":PATH,"cutoff_at":CUTOFF}]
        r=audit_first_add(records,fetch=lambda route:(_ for _ in ()).throw(OSError("down")),
                          repository=REPO)
        self.assertEqual(r["checked_count"],0)
        self.assertEqual(len(r["errors"]),1)
        self.assertEqual(r["independently_verified_first_seen_count"],0)
    def test_maximum_file_limit_does_not_certify_omitted_items(self):
        rows=[{"path":f"t12_baselines/20261103/2026110307{i:02d}.json",
               "cutoff_at":CUTOFF} for i in (8,9)]
        r=audit_first_add(rows,fetch=lambda route:fetch(route),repository=REPO,limit=1)
        self.assertEqual(r["unexamined_due_to_limit"],1)
        self.assertEqual(r["checked_count"],1)
    def test_no_records_is_valid_empty_audit(self):
        r=audit_first_add([],fetch=lambda route:self.fail("no API on empty"),repository=REPO)
        self.assertEqual(r["checked_count"],0)
        self.assertEqual(r["unexamined_due_to_limit"],0)


if __name__=="__main__":unittest.main()
