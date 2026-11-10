# P0 batch 03 — all 117 indexed legacy Git blobs checked (2026-11-04 JST)

Pinned old source: `ikst2512-eng/boat-edge` commit `f38204105a979aa6ef5293d1b9cad854056faadd`. Used **exactly** the third 25-race P0 plan CSV `batches/p0_batch_03_of_45.csv` from the frozen 45-batch package. Actual read-only GitHub `fetch_file` calls returned 117 source JSON objects. Each GitHub-reported Git blob SHA1 was reconciled locally with the batch plan's expected blob SHA1.

| Source category | Indexed source paths | Fetched | Git blob SHA1 matches |
|---|---:|---:|---:|
| Forecast | 25 | 25 | 25 |
| Prediction audit | 25 | 25 | 25 |
| History | 25 | 25 | 25 |
| Result | 25 | 25 | 25 |
| Odds | 17 | 17 | 17 |
| **Total** | **117** | **117** | **117** |

The eight odds paths not included in the frozen third batch were marked `NOT_INDEXED`, not artificially fetched or reconstructed. All 25 returned result JSONs had `status=confirmed`; each of the 17 odds objects contained 120 trifecta combinations.

Machine-readable receipt `boat_edge_p0_batch03_117_git_blob_receipt_20261104.csv` covers all 125 possible slots (117 MATCH, 8 NOT_INDEXED), SHA256 `f5c5b6f0b319051f8abbddea8e836584f7f3e4c85c38b7dc1d657ac1f0652c42`. Local comparator `build_p0_batch03_receipt_20261104.py` asserted 117 Git matches and zero mismatches against the immutable batch CSV. This receipt is **metadata only, not original-source bytes**.

**Cumulative Git source checks**: batches 01–03 cover 75 distinct P0 races and **118 + 115 + 117 = 350** indexed source Git objects, all expected Git blob IDs matched. These checks do not establish source-byte export, independently backed-up source custody, cold restored SHA256, prediction Fresh status, or permission to stop legacy writers.

Independent off-service P0 source custody remains **only one previously backed-up Kiryu 5R odds original**; 412 archived result originals are P1/P2 only (P0=0). The 5,578-indexed P0 original backup is unfinished. No old prediction files, CI/Actions, UI, Pages, or other teams' code were changed.

**DELETE_BLOCKED / LEGACY_WRITER_STOP_BLOCKED. Draft PR unmerged.**