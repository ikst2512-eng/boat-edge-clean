# P0 source path existence and Git blob identity, first five races — 2026-11-04

This run directly queried **24 source JSON objects** from the pinned old repository revision `f38204105a979aa6ef5293d1b9cad854056faadd` through authenticated GitHub file-fetch API. It independently compared the GitHub-returned blob IDs with the frozen P0 crosswalk, programmatically, using the local read-only comparator `check_p0_first5_direct_fetch_20261104.py`.

| P0 race | Snapshot | Audit | History | Odds | Result |
|---|---|---|---|---|---|
| `20261008-01-03` | MATCH | MATCH | MATCH | NOT_INDEXED | MATCH |
| `20261008-01-04` | MATCH | MATCH | MATCH | MATCH | MATCH |
| `20261008-01-05` | MATCH | MATCH | MATCH | MATCH | MATCH |
| `20261008-01-06` | MATCH | MATCH | MATCH | MATCH | MATCH |
| `20261008-01-07` | MATCH | MATCH | MATCH | MATCH | MATCH |

**24/24 indexed file reads succeeded and all 24 Git blob IDs matched the pinned retention matrix exactly.** Kiryu 3R odds remains one of the historically unindexed 46 odds references; no substitute or synthetic original was created. This verifies **Git object availability and declared blob identity**, **not** a separate local source-byte SHA256 calculation, and **not** off-service retention. Source bytes are still held by the old Git repo; the connector response was not transferred to any independent destination.

The machine-readable 25-row receipt `boat_edge_p0_first5_direct_git_receipt_20261104.csv` SHA256 `987f1ff8dee1589f76eca48896fc4283053c926d94949af2fc9feb4b394f210e` documents the exact files, expected/fetched Git blob IDs, the unindexed odds path, and `bytes_in_independent_backup=false` for each line. It is **metadata only** (no historical original file bytes). Existing stored Kiryu 5R odds original is a separate prior off-service verification and must not be double-counted from this receipt.

This establishes a viable **read-only pinned GitHub connector path for a small batch**, but does not establish a bulk, independently exportable backup route for all 5,578 original files. The previously blocked connector-to-Drive original forecast transfer was **not retried or circumvented**. A dedicated permitted export path and off-service readback remain required before P0 source custody is certified.

Legacy writer and original bytes unchanged. Draft PR #1559 remains unmerged. **DELETE_BLOCKED / LEGACY_WRITER_STOP_BLOCKED.**