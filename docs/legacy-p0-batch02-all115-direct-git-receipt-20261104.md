# P0 batch 02: 115/115 pinned Git source-file identities verified — 2026-11-04 JST

**Scope:** The second 25-race P0 batch from the fixed 45-batch plan. No production code, old system, historical original data, model or workflow changes.

Legacy Git revision: `f38204105a979aa6ef5293d1b9cad854056faadd`. The exact pinned batch manifest file is `batches/p0_batch_02_of_45.csv` in `boat_edge_p0_45_batch_preservation_plan_20261104.zip`.

## Direct file retrieval and source reconciliation

All **115 indexed original JSON paths** were directly fetched via the authenticated old-Git repository `fetch_file` connector. Each fetched document's Git blob SHA1 from the GitHub response was compared against the independently frozen batch CSV source path's expected Git SHA1.

| Original category | Indexed | Direct fetch | Expected Git blob matched |
|---|---:|---:|---:|
| Forecast snapshot | 25 | 25 | 25 |
| Prediction audit | 25 | 25 | 25 |
| Prediction history | 25 | 25 | 25 |
| Result | 25 | 25 | 25 |
| Odds | 15 | 15 | 15 |
| **Total** | **115** | **115** | **115** |

All fetched forecast JSONs had expected race-key IDs. All 25 result originals reported `status=confirmed`, and all 15 odds JSONs contained 120 trifecta entries. **10 odds paths were NOT_INDEXED** in this batch, and they were not replaced or synthesized.

A typographical transcription error in **one manually transcribed source SHA1 string** initially yielded 114/115 matches in the temporary receipt. It was corrected by referencing the actual original GitHub fetch response (`20261008-05-07` forecast blob `2438b0de28dcf4d619683dd19458bb578d1dd97c`), and the entire batch compared again: **115/115 MATCH**, source mismatch 0. This was a receipt-entry typo, not a Git original mutation or SHA1 collision. Always distinguish connector-reported blob verification from independently recomputing content hashes.

**Portable read-only receipt artifacts:** `boat_edge_p0_batch02_115_git_blob_receipt_20261104.csv` SHA256 `aa76c9ce39881aa731d886d7bef83f5a4fdee5fedfdd1ff7c2a3deb09b2f45ac`, plus comparison script and summary JSON in `boat_edge_p0_batch02_direct_git_verification_20261104.zip` SHA256 `f88a4ebb1efa38c5373c25cd08aad265b1a8fdf9e9204dd491ab6b352c3db1b7`. The ZIP test passed.

## What did NOT happen

This is proof of Git object availability and matching **reported** blob identifiers, not independent SHA256 readback of archived original source bytes. The portable artifacts contain metadata and scripts only. No new batch 02 originals were copied to an off-GitHub custody provider or restored from it. P0 independently recovered original source bytes remain **one** previously archived Kiryu 5R odds source; the 412 offsite result originals are P1/P2 (P0=0).

P0 indexed original byte restoration across **5,578 files** and 1,125 forecast races is not complete. Do not stop old writer, archive away the only working repository, delete data, or promote prior SITE references to formal Fresh.

**DELETE_BLOCKED / LEGACY_WRITER_STOP_BLOCKED. Draft PR unmerged.**