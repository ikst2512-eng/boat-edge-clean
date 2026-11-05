# P0 batch 01: complete 118-of-118 indexed Git-source object verification (2026-11-04 JST)

**Fixed legacy Git source:** `ikst2512-eng/boat-edge` at `f38204105a979aa6ef5293d1b9cad854056faadd`. **Batch:** first 25 P0 race rows from the deterministic 45-batch plan.

## Actual authenticated source reads

All 118 indexed file paths were requested directly via GitHub `fetch_file`; all requests succeeded and returned Git blob SHA1s that match exactly the pinned `batches/p0_batch_01_of_45.csv` source references. The first 25 snapshot reads were previously documented, and the remaining **93** were independently fetched now and checked against the immutable matrix using a locally executable Python comparison. Breakdown:

| Source file category | Indexed paths | GitHub fetch successes | Expected Git blob ID matches |
| --- | ---: | ---: | ---: |
| `data/site_prediction_snapshots` | 25 | 25 | 25 |
| `data/site_prediction_audit` | 25 | 25 | 25 |
| `data/site_prediction_history` | 25 | 25 | 25 |
| `data/site_odds` | 18 | 18 | 18 |
| `data/site_results` | 25 | 25 | 25 |
| **Total** | **118** | **118** | **118** |

Seven snapshot races lack an indexed odds reference in batch 01 (the 46 unindexed P0 odds source issue remains). No odds originals were synthesized or retrospectively attached. All 25 result JSON objects declare `status=confirmed`; all 18 odds JSON files returned 120 three-way combination entries.

The newly created 93-row `boat_edge_p0_batch01_remaining93_git_blob_receipt_20261104.csv` has **93/93 verified expected blob matches and zero mismatches**, SHA256 `8924650cb9b5e8ba94fff4ccdc65b2febee4f6e3094970e6efc8290b8185fbbd`. The previously created 25-row forecast receipt remains a distinct companion record. The local verifier source `verify_p0_batch01_remaining_20261104.py` repeats expected-vs-returned blob comparison; this is a **metadata receipt**, not raw original contents.

## Acceptance boundary

These are GitHub-reported blob identities checked against pinned historical Git source paths; **not** the same as having all 118 original bytes locally saved, SHA256-verified from a cold backup, or re-read from Google Drive. No P0 batch has yet passed the independent-offsite custody/restore gate. The previously preserved Kiryu 5R original odds is the single separately validated P0 byte-original off GitHub; the archived 412 results belong to P1/P2 (P0=0).

The connector-to-Drive transfer of forecast source bytes had previously been safety-blocked; that workflow was not retried by a substitute. Do not authorize source deletion, old site shutdown or formal Fresh promotion based on source-existence checks alone.

**DELETE_BLOCKED / LEGACY_WRITER_STOP_BLOCKED.** Current active site, old Git original files, CI/Actions/Pages, other teams' code and predictions are unchanged; Draft PR remains unmerged.