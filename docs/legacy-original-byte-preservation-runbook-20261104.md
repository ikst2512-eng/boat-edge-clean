# P0 original-byte preservation execution handoff — 2026-11-04 JST

Scope: no changes to legacy/CLEAN originals, production, CI, prediction models, results, odds or Actions. This is a **read-only retrieval procedure** for the previously identified 1,125 legacy-only prediction snapshot races. No shutdown authorization.

## Prepared local portable toolkit (outside GitHub source)

- `boat_edge_original_preservation_toolkit_20261104.zip`: SHA256 `089d98b44827c3fac0a560694e0bee4dd1dc54da3958cafe5ba2e51c443c65d7`.
- Contains `legacy_original_preserver.py` and `boat_edge_legacy_retention_race_matrix_20261104.csv` (4,143 race records), plus `manifest.json`. The CSV SHA256 is `49d00beb719dd3efe45e5dd659ff5075309ac41f14147ef10cc9c2840deabb67`. The Python script SHA256 is `afced58a38e4a2b318a40bc42451df60dfcd89075618834edb70e13360882570`.
- **No actual source originals** are included in this toolkit. The ZIP is a portable executable inspection handoff, not a backup of those originals.

## Tool contract and tested behavior

Run from a **network-capable machine** with local independent storage, Python 3.10+:

```bash
python legacy_original_preserver.py --matrix boat_edge_legacy_retention_race_matrix_20261104.csv --dest /independent/boat-edge-originals --priority P0 --limit 5
# Inspect dry run: no fetches or writes
python legacy_original_preserver.py --matrix boat_edge_legacy_retention_race_matrix_20261104.csv --dest /independent/boat-edge-originals --priority P0 --limit 5 --execute
```

With `--execute`, it downloads each indexed source at immutable legacy Git tree SHA via GitHub Raw; verifies the **actual Git blob hash computed over the returned bytes** against the original index; calculates SHA256; stores original bytes in a separate directory without overwriting a different existing file; reads them back and checks SHA256. Writes a per-source `local_readback_manifest.json`. The manifest explicitly marks `independent_backup_verified=false` and `git_first_add_verified=false`; local readback is not external durable replication. No credentials are logged or committed.

Tests executed in current sandbox:
- Dry-run P0 first 5 races: 24 original file references, zero writes.
- Test Git blob SHA1 algorithm with known Git fixture.
- Reject path traversal.
- Mocked source download, immutable write, SHA256 readback and manifest generation: passed.
- Toolkit ZIP member SHA256 verification: passed.
- **External actual source download failed/was not executed** from the sandbox due to no DNS/network access to `raw.githubusercontent.com`. Therefore there is **no claimed real-original SHA256 preservation success** in this execution.

## Remaining safety gates

- Run on a network-capable host with independent durable backup, starting with the small sample; inspect failures and confirm 1,125-race coverage, *not* just attempted counts. Some historically missing sources may produce 404 and must be recorded, not synthesized.
- Snapshot raw source alone is insufficient: obtain first Git-add commit/time, source-receipt/odds/settlement provenance; distinguish SITE_ONLY from formal Fresh, and verify restored evidence after off-host replication.
- Do not merge this toolkit into production CI, change scheduled workflows, auto-import old predictions, stop Pages/old writers, or delete originals.

**DELETE_BLOCKED / LEGACY_WRITER_STOP_BLOCKED.**
