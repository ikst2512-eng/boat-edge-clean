"""Real SQLite tests for the SQL embedded in the proposed D1 Worker.

No network / Cloudflare account / D1 deployment / GitHub write.
"""
import concurrent.futures
import pathlib
import re
import sqlite3
import tempfile
import threading
import unittest

ROOT = pathlib.Path(__file__).resolve().parent
SRC = (ROOT / "hole_pair_first_receipt_worker.mjs").read_text("utf8")
SCHEMA = (ROOT / "hole_pair_first_receipt_schema.sql").read_text("utf8")

# The Worker stores the query as JS string-array elements joined by newline.
BLOCK = re.search(r"export const INSERT_SQL = \[(.*?)\]\.join\(\"\\n\"\);", SRC, re.S)
assert BLOCK, "Worker INSERT_SQL declaration not found"
QUOTED = re.findall(r'^\s*("(?:[^"\\]|\\.)*"),?\s*$', BLOCK.group(1), re.M)
assert len(QUOTED) == 6, "INSERT SQL changed; inspect SQL test parser"
import json
INSERT = "\n".join(json.loads(line) for line in QUOTED)


class D1FirstAcceptanceSQLiteTests(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.db_now = "2026-11-09T01:55:00Z"

    def insert(self, code="202611090101", sha="a"*64,
               cutoff="2026-11-09T02:00:00.000Z", body="{}",
               finish="2026-11-09T01:51:00.000Z"):
        sql = INSERT.replace("strftime('%s', 'now')",
                             "strftime('%s', '" + self.db_now + "')")
        return self.conn.execute(sql, (code, sha, body, cutoff, cutoff, finish)).fetchone()

    def test_first_insert_and_idempotent_duplicate(self):
        self.assertEqual(self.insert()["race_code"], "202611090101")
        self.assertIsNone(self.insert())
        self.assertEqual(self.conn.execute(
            "SELECT count(*) FROM hole_pair_first_receipts").fetchone()[0], 1)

    def test_late_identical_retry_preserves_original_first_row(self):
        # An old, valid receipt may be read back after cutoff, but a retry
        # cannot produce a second first-receipt timestamp or replace its bytes.
        first = self.insert(body='{"immutable":"original"}')
        self.assertIsNotNone(first)
        original = dict(self.conn.execute(
            "SELECT * FROM hole_pair_first_receipts WHERE race_code = ?",
            ("202611090101",)).fetchone())
        self.db_now = "2026-11-09T02:10:00Z"
        self.assertIsNone(self.insert(body='{"immutable":"original"}'))
        self.assertIsNone(self.insert(sha="b"*64,
                                      body='{"immutable":"revision"}'))
        stored = dict(self.conn.execute(
            "SELECT * FROM hole_pair_first_receipts WHERE race_code = ?",
            ("202611090101",)).fetchone())
        self.assertEqual(stored, original)
        self.assertEqual(self.conn.execute(
            "SELECT COUNT(*) FROM hole_pair_first_receipts").fetchone()[0], 1)

    def test_same_race_changed_cutoff_cannot_rewrite_first_receipt(self):
        self.assertIsNotNone(self.insert())
        original = dict(self.conn.execute(
            "SELECT * FROM hole_pair_first_receipts").fetchone())
        # A later claimed cutoff must never make a different first record.
        self.assertIsNone(self.insert(
            sha="b"*64, body='{"changed":"cutoff"}',
            cutoff="2026-11-09T02:30:00.000Z",
            finish="2026-11-09T01:52:00.000Z"))
        self.assertEqual(dict(self.conn.execute(
            "SELECT * FROM hole_pair_first_receipts").fetchone()), original)

    def test_later_distinct_race_still_accepts_before_own_cutoff(self):
        # Per-race idempotency must not become a same-day write lock.
        self.assertIsNotNone(self.insert(code="202611090101"))
        self.db_now = "2026-11-09T02:10:00Z"  # Race 01 already past cutoff
        self.assertIsNotNone(self.insert(
            code="202611090102", sha="b"*64,
            cutoff="2026-11-09T02:20:00.000Z",
            finish="2026-11-09T02:08:00.000Z"))
        self.assertEqual([r[0] for r in self.conn.execute(
            "SELECT race_code FROM hole_pair_first_receipts ORDER BY race_code"
        ).fetchall()], ["202611090101", "202611090102"])
        self.assertIsNone(self.insert(code="202611090101"))

    def test_same_second_early_margin_denies_new_insert(self):
        for now in ("2026-11-09T01:59:58Z", "2026-11-09T01:59:59Z",
                    "2026-11-09T02:00:00Z", "2026-11-09T02:05:00Z"):
            self.db_now = now
            with self.subTest(now=now):
                self.assertIsNone(self.insert())
        self.assertEqual(self.conn.execute(
            "SELECT count(*) FROM hole_pair_first_receipts").fetchone()[0], 0)

    def test_two_seconds_plus_margin_succeeds(self):
        self.db_now = "2026-11-09T01:59:57Z"
        self.assertIsNotNone(self.insert())

    def test_database_rejects_receipt_before_calculation_finish(self):
        self.db_now = "2026-11-09T01:50:00Z"
        self.assertIsNone(self.insert())

    def test_sqlite_generates_timestamp_not_caller(self):
        row = self.insert(body='{"claimed_received_at":"1999-01-01"}')
        self.assertNotIn("1999-01-01", row["first_received_at_utc"])
        self.assertRegex(row["first_received_at_utc"], r"^\d{4}-\d{2}-\d{2}T")

    def test_existing_row_cannot_be_updated(self):
        self.insert()
        with self.assertRaisesRegex(sqlite3.IntegrityError, "immutable_update"):
            self.conn.execute(
                "UPDATE hole_pair_first_receipts SET candidate_sha256 = ?",
                ("b"*64,))
        self.assertEqual(self.conn.execute(
            "SELECT candidate_sha256 FROM hole_pair_first_receipts").fetchone()[0],
            "a"*64)

    def test_existing_row_cannot_be_deleted(self):
        self.insert()
        with self.assertRaisesRegex(sqlite3.IntegrityError, "immutable_delete"):
            self.conn.execute("DELETE FROM hole_pair_first_receipts")
        self.assertEqual(self.conn.execute(
            "SELECT count(*) FROM hole_pair_first_receipts").fetchone()[0], 1)

    def test_unsafe_parameters_cannot_break_schema(self):
        invalid = "202611090101'); DROP TABLE hole_pair_first_receipts; --"
        self.assertIsNone(self.insert(invalid))
        self.assertEqual(self.conn.execute(
            "SELECT name FROM sqlite_master WHERE name='hole_pair_first_receipts'"
        ).fetchone()[0], "hole_pair_first_receipts")

    def test_sql_check_constraints_ignore_bad_data(self):
        # INSERT OR IGNORE silently refuses CHECK failures; no row is created.
        self.assertIsNone(self.insert(sha="x"))
        self.assertIsNone(self.insert(body="X"*40000))
        self.assertEqual(self.conn.execute(
            "SELECT count(*) FROM hole_pair_first_receipts").fetchone()[0], 0)


    def _parallel_first_inserts(self, submissions):
        """Exercise the exact Worker INSERT on independent SQLite connections.

        An on-disk WAL database, not a mock map, arbitrates simultaneous
        candidates. The artificial SQLite clock only keeps the fixture fixed.
        This is NOT proof of deployed D1 behavior or independent time.
        """
        with tempfile.TemporaryDirectory() as temporary:
            database = str(pathlib.Path(temporary) / "research-receipts.sqlite3")
            setup = sqlite3.connect(database, isolation_level=None)
            try:
                setup.execute("PRAGMA journal_mode=WAL")
                setup.executescript(SCHEMA)
            finally:
                setup.close()
            barrier = threading.Barrier(len(submissions))
            sql = INSERT.replace(
                "strftime('%s', 'now')",
                "strftime('%s', '2026-11-09T01:55:00Z')",
            )

            def attempt(item):
                code, digest = item
                connection = sqlite3.connect(database, timeout=10, isolation_level=None)
                try:
                    connection.execute("PRAGMA busy_timeout=10000")
                    barrier.wait(timeout=5)
                    return connection.execute(sql, (
                        code, digest, '{"test":"nonformal"}',
                        "2026-11-09T02:00:00.000Z",
                        "2026-11-09T02:00:00.000Z",
                        "2026-11-09T01:51:00.000Z",
                    )).fetchone() is not None
                finally:
                    connection.close()

            with concurrent.futures.ThreadPoolExecutor(
                max_workers=len(submissions)
            ) as pool:
                inserted = list(pool.map(attempt, submissions))
            check = sqlite3.connect(database)
            try:
                rows = check.execute(
                    "SELECT race_code, candidate_sha256 FROM "
                    "hole_pair_first_receipts ORDER BY race_code"
                ).fetchall()
            finally:
                check.close()
            return inserted, rows

    def test_simultaneous_conflicting_same_race_writes_at_most_one_row(self):
        # Two distinct bytes (two SHA256s) must never both become first.
        submissions = [
            ("202611090101", "a" * 64),
            ("202611090101", "b" * 64),
        ]
        inserted, rows = self._parallel_first_inserts(submissions)
        self.assertEqual(sum(inserted), 1)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], "202611090101")
        self.assertIn(rows[0][1], {"a" * 64, "b" * 64})

    def test_simultaneous_identical_retries_insert_exactly_once(self):
        # Four racing identical submissions cannot increment the denominator.
        submissions = [("202611090101", "a" * 64)] * 4
        inserted, rows = self._parallel_first_inserts(submissions)
        self.assertEqual(sum(inserted), 1)
        self.assertEqual(rows, [("202611090101", "a" * 64)])

    def test_parallel_distinct_race_ids_keep_both_first_receipts(self):
        # Unlike the daily once-only gateway, first-write uniqueness is per
        # race_code; a later independent race must not be suppressed.
        submissions = [
            ("202611090101", "a" * 64),
            ("202611090102", "b" * 64),
        ]
        inserted, rows = self._parallel_first_inserts(submissions)
        self.assertEqual(sum(inserted), 2)
        self.assertEqual([row[0] for row in rows],
                         ["202611090101", "202611090102"])


if __name__ == "__main__":
    unittest.main()
