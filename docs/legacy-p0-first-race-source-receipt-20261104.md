# P0 source retrieval receipt — 2026-11-04 JST

This is a **read-only connector fetch** for the first prioritized legacy-only prediction race, not a successful independent byte archive. No original changed.

## Pinned Git source

- Legacy tree: `f38204105a979aa6ef5293d1b9cad854056faadd`.
- Race: `20261008-01-03` / Kiryu 3R, 2026-10-08.
- Archived snapshot model: `SITE_REFERENCE_V122`.
- Race deadline in snapshot: `16:22` JST; embedded `first_saved_at=2026-10-08T07:15:40.108392+00:00` and `minutes_to_deadline=6.33`. **This embedded timestamp is not independent proof of the first Git-add time.**
- PRE_RESULT guards in snapshot all false (`results_seen`, `unlock`, `scoring`), and audit `pass=true`. These are source-declared flags, not a formal Fresh certification.

| Pinned original | Direct connector Git blob SHA | Matches prior race matrix |
| --- | --- | --- |
| `data/site_prediction_snapshots/20261008-01-03.json` | `4758d57a765ee06c56a8f85680b7d600728677ca` | YES |
| `data/site_prediction_audit/20261008-01-03.json` | `90da096812e09ef6aad9bbeb9f99846a12f302b5` | YES |
| `data/site_prediction_history/20261008-01-03.json` | `ad959b67738bb7c119b21d5fde26587908f66bcc` | YES |
| `data/site_results/20261008-01-03.json` | `7f706cb2296e01079b6d0742b4973eb04713a9b9` | YES |

Four JSON responses parsed and `race_key` matched. Result shows winning trifecta `1-2-3` and `trifecta_payout_yen_per_100=3630`; audit settlement agrees on `1-2-3`. No associated `site_odds` file was indexed for this race in the preservation matrix. This is a **gap for source-odds preservation**, not reason to reconstruct odds from later values.

## Actual source-byte backup limitation

- Attempted HTTPS fetch to `raw.githubusercontent.com` from current container was blocked by DNS `Temporary failure in name resolution`.
- Direct connector returned JSON content and its Git blob identity; **no 4-file independent original byte bundle was written, no raw-byte SHA256 readback was performed**.
- The local preserver dry-run still plans five P0 races / 24 file references, zero writes.
- The separate standalone toolkit exists for an operator in a network-capable host but cannot be treated as an executed real backup.

**STOP/DELETE/MIGRATE all remain blocked.** Keep source forecasts separate from CLEAN, and do not infer formal eligibility from embedded flags.

## Follow-up: first Git-add evidence found and linked

- The legacy post-settlement, site-only evaluation `data/site_learning/site_mode_evaluations_v136/20261008-01-03.json` at pinned tree stores `first_git_snapshot_commit=1d06d01b5cae217f137e71a5a69e92c9ef7fb208` and `scope=SITE_REFERENCE_POST_SETTLEMENT_ONLY_NOT_FORMAL_FRESH`.
- Direct GitHub fetch of commit [1d06d01](https://github.com/ikst2512-eng/boat-edge/commit/1d06d01b5cae217f137e71a5a69e92c9ef7fb208) reports timestamp `2026-10-08T07:15:40Z` and includes `data/site_prediction_snapshots/20261008-01-03.json` with a new-file patch header `@@ -0,0 +1,279 @@`. This substantiates that the source file was added in that commit, not merely self-declared in JSON. Commit timestamp alone is not an independent proof of wall-clock event ordering, so preserve receipt confidence separately.
- Direct fetch of that path *at the alleged first-add commit* gives blob `4758d57a765ee06c56a8f85680b7d600728677ca`, identical to the original pinned-tree source and previously indexed hash. This is a Git blob identity verification, **not** an off-host independent SHA256 restore.
- Direct fetch at pinned tree of `data/site_odds/20261008-01-03.json` and `data/site_autopilot/v229_evidence/20261008-01-03.json` returned GitHub 404. Snapshot declares `odds_sha256=null`; source odds coverage is **NOT VERIFIED**. Do not invent an odds sidecar or mark official 120 odds present.
- Mark this single race as `FIRST_GIT_ADD_COMMIT_OBSERVED` and `SOURCE_BLOB_MATCH`, while `ODDS_SOURCE_MISSING`, `INDEPENDENT_BYTES_BACKUP_UNVERIFIED`, and `FORMAL_FRESH_NOT_APPLICABLE` remain. No generalization to the other P0 races.
