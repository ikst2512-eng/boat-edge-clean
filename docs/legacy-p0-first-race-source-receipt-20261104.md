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
