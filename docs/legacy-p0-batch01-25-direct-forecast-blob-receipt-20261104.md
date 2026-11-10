# P0 batch 01: 25 historical forecast snapshots directly verified (2026-11-04 JST)

**New real GitHub source reads, no source mutation and no offsite-byte preservation claim.**

Fixed legacy commit: `f38204105a979aa6ef5293d1b9cad854056faadd`. Read **25/25 JSON prediction snapshots** from `data/site_prediction_snapshots/{race_id}.json` through the authenticated read-only GitHub fetch-file connector; all 25 fetched objects were parseable JSON with corresponding race IDs and original SITE prediction modes.

Independently compared each returned Git blob SHA1 against the **first 25-row batch** in the immutable `boat_edge_p0_45_batch_preservation_plan_20261104.zip` source reference matrix. **25/25 Git blob SHA1 MATCH; 0 missing, 0 mismatch.** IDs cover 2026-10-08 Kiryu 3–12R, Toda 1–10R and 12R, and Tamagawa 1–4R. The first five were previously verified across all 24 indexed source types, so do not count those five as newly added unique races.

A 25-row local receipt `boat_edge_p0_batch01_25_forecast_direct_blob_receipt_20261104.csv` was generated against the exact archived batch CSV using `make_p0_batch01_snapshot_receipt_20261104.py`. Receipt SHA256: `704351454f2fbb36e614ad01cfc6be116de13822bcab2c98cd0a0e1ab01dbbb0`.

**Precise distinction:** This operation fetched JSON text from the old pinned Git repository and verified the GitHub-returned blob ID against the retention matrix. The receipt contains **metadata only**; actual downloaded original source bytes have **not** been packed into a durable original archive, downloaded from an independent provider, or independently re-hashed after restored source-byte export. Do not mark them as protected or formal Fresh. The previously blocked cross-service source-original transfer was not attempted again.

Existing independently restored P0 original-byte count remains the *single Kiryu 5R odds file*, **not 25 forecast files**. Archived result originals total 412 across P1=61/P2=351 with P0=0. All 5,578 indexed P0 original sources still need independent byte archival / byte readback before retiring old writers.

**DELETE_BLOCKED / LEGACY_WRITER_STOP_BLOCKED.** Only this documentation-only Draft PR branch was updated.