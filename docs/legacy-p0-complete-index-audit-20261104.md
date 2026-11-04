# P0 complete index-integrity audit — 2026-11-04 JST

This is a **read-only source-reference audit**, not an independent original-byte backup, a retrospective rewrite of old forecasts, or authorization to stop legacy systems. Issues #708/#329; extend Draft PR #1559.

## Verified, repeatable numbers

Input: prior legacy/CLEAN pinned crosswalk transformed into `boat_edge_legacy_retention_race_matrix_20261104.csv`, 4,143 rows, SHA256 `49d00beb719dd3efe45e5dd659ff5075309ac41f14147ef10cc9c2840deabb67`. P0 subset has **1,125 legacy-only prediction races**.

| Index presence metric | P0 races |
| --- | ---: |
| snapshot, audit, result indexed | 1,125 each |
| odds indexed | 1,079 |
| odds **not indexed** | **46** |
| history indexed | 1,124 |
| history **not indexed** | **1** |
| all five source categories indexed | **1,078** |
| missing odds + missing history overlap | 0 |

The **46 and 1 are disjoint**, so 47 P0 race IDs lack at least one of these five references. Indexed ≠ successfully fetched ≠ SHA-verifiable ≠ externally backed up. This is a *presence index*, not proof that the missing file never existed at another path, or that current other source bytes are identical.

Fixed legacy pinned commit for this crosswalk: `f38204105a979aa6ef5293d1b9cad854056faadd`. Three spot checks at that tree returned 404: `data/site_odds/20261008-01-03.json`, `data/site_odds/20261008-01-10.json`, `data/site_prediction_history/20261008-14-05.json`.

## Regression-hardening against SHA false-positive mistakes

An **off-repository** inspection package `boat_edge_p0_integrity_audit_20261104.zip` was generated, SHA256 `cde3a57cbd29bfec2a85a7256161541f2f74c8f2615108c95e95f6b8958e4609`. Package includes existing four-thousand-race CSV, 1,125-row P0 inspection JSON, `legacy_p0_integrity_audit.py` and its test suite plus hash manifest.

- JSON report hash: `8dd9439d89f8b9a236a21a11168555e9e37d4adcd30b0fc6633e756d62b04c27`.
- **8/8 unit tests PASS:** SHA256 vectors/independent calls, real-byte mocked readback, modified-byte failure, missing local file not success, symlink denial, traversal denial, duplicate-race denial, unknown index distinguished from actual file loss.
- Uses Python `hashlib.sha256` **for each byte string separately**, never a manually stateful SHA256 routine. Git blob SHA1 is separately computed in Git's `blob {length}\0{bytes}` format.
- Optional `--originals` verifies already-retrieved local originals without writing to them; a successful local readback is **not** proof of replication to an off-host durable destination. Local source absence is `NOT_PRESENT`; no matrix entry is `NOT_INDEXED`; these states are never conflated.
- Package contains indexes/scripts/reports, **not source originals**. It does not execute GitHub network retrieval itself and should not be copied into production CI as a new writer.

## Risk and next acceptance gate

Verify the 47 gaps by searching alternative same-race source locations / historic commits; do not synthesize missing odds or history. For every P0 indexed source, retrieve exact original bytes via existing standalone preservation tool, SHA-verify against indexed Git blob, replicate to independent durable storage, read back from that destination and validate per-file SHA256, preserving first Git commit and chronology. Non-verified originals remain blocked, and old site/scripts remain on.

**No source file, prediction, result, odds, workflow, Pages or other-team production code was modified. DELETE_BLOCKED / LEGACY_WRITER_STOP_BLOCKED.**
