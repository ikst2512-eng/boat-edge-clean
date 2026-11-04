# Independent local byte-readback of legacy RESULT originals — 2026-11-04 JST

Scope: **historical result original bytes only**, not source forecasts or odds. Read-only checkout of previously completed Actions artifacts, no old-site writer, Pages, model, CLEAN site, results, or production data change. Issue #708/#329.

## Source artifacts downloaded and verified locally

| Run | GitHub artifact | ZIP byte SHA256 verified | Embedded result originals |
| --- | ---: | --- | ---: |
| `40739572811` | `12838409473` | `755b694e13665ab7d66f7a2e0d03e2d47c4bf9c630025fc2215ef8cfb7fa3814` | 292 |
| `40936953310` | `12924304439` | `9460f06cc712a87756ef4f54feb0612d63c812562b6486be12491e48be10e216` | 412 |

Each ZIP carries `legacy_result_originals.tar.gz`, `legacy_blob_readback.json`, `restore.json`, etc. Reopened each ZIP and tarball with Python stdlib `zipfile`, `tarfile`, `hashlib`. No filesystem extraction or potential tar path traversal.

- **292/292** old artifact originals: actual TAR-member bytes SHA256 **and** Git `blob {length}\0{data}` SHA1 match audit records.
- **412/412** newer artifact originals: actual TAR-member bytes SHA256 **and** Git blob SHA1 match audit records.
- **292 overlapping race IDs** between artifacts have identical SHA256 and Git blob IDs, **0 cross-artifact conflicts**. Newer artifact has **120 extra race result originals**; total unique **412**.
- Both artifacts have zero unindexed/missing originals and zero unsafe member names in this check.
- `restore.json` declares `sha256_restore_passed=true`, `durable_offsite_backup_verified=false`, `fresh_prediction_evidence_preserved=false`. The direct local byte comparison above was newly performed and is not merely repeating that embedded claim. `verification.json` says `official_payout_verified=false`: do not imply external official payout validation.
- Newer source artifact expires **2027-01-27T19:05:55Z**; older source artifact expires **2027-01-26T17:50:52Z**. These are expiring hosted copies, **not** durable independent cold storage.

## Verified operator-downloadable archive

A smaller local export `boat_edge_verified_412_legacy_results_20261104.zip` was generated from the authenticated newer source artifact with the 412 original result JSON bytes retained in `legacy_result_originals.tar.gz`, original blob manifest, original restore claims, independent local reconciliation CSV/report, and a self-contained read-only `verify_bundle.py` script.

- **Export ZIP SHA256:** `46c1d2433d97619bea3e686ff919a8d649d17636ec4308dbb3a3fb7615f0f38f`.
- **Direct verification after repacking:** `PASS: 412/412 original result bytes, SHA256 and Git blob SHA1; no missing/unsafe members`.
- Source `legacy_results_recovered_byte_manifest_20261104.csv` logs both artifact sources and 704 verified source observations (412 distinct races).
- This output currently lives only in the conversation working environment as downloadable user artifact. **It has NOT been uploaded to an independent persistent storage destination or retrieved from there**, and therefore **must not be described as meeting retirement durable-offsite gate**. An operator can copy it to a separate secure durable destination and independently rerun `python verify_bundle.py <archive>`.

## Gate status

- **RESULT-BYTES-LOCAL-RELOAD = PASS for 412 historical results.**
- **FORECAST-BYTES-LOCAL-RELOAD = NOT TESTED** (1,125 P0 forecast originals remain pending).
- **ODDS-BYTES-LOCAL-RELOAD = NOT TESTED** for full cohort.
- **DURABLE-OFFSITE-RELOAD = NOT VERIFIED** for any cohort here.
- **FORMAL FRESH / payout audit acceptance = NOT CLAIMED.**

**DELETE_BLOCKED / LEGACY_WRITER_STOP_BLOCKED.** Do not halt or remove any old workflow, Pages service, or original solely based on this result-only archive.
