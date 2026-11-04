# Hardened P0 recovery tool: original-file write-path audit (2026-11-04 JST)

**Scope:** 1,125 legacy-exclusive P0 races; 5,578 indexed original files across 45 batches. This note describes an **offline tool audit**, not recovery of 5,578 originals.

Reviewed original standalone `legacy_original_preserver.py` from the existing ZIP `boat_edge_original_preservation_toolkit_20261104.zip`. The previous script validated source relative paths and Git SHA, and refused overwrite of existing target *contents*. However, it used `Path.mkdir(..., exist_ok=True)` and followed symbolic-link ancestors / targets without explicit symlink-safe traversal; under a hostile or accidentally redirected destination tree, it could write outside intended evidence directory. In addition, re-running a finalized directory was not blocked until after its fetch loop, although it would later refuse overwriting the manifest.

A standalone hardened version `legacy_original_preserver_hardened_20261104.py` now performs **preflight rejection before network writes** when the destination root or any expected original's ancestor / target is a symbolic link, an existing intermediate component is not a directory, a source path or pinned Git reference is invalid, duplicate races or duplicate sources occur, or a finalized `local_readback_manifest.json` already exists. File creation uses exclusive flags `O_CREAT|O_EXCL` and `O_NOFOLLOW` where available. It retains source Git blob SHA1 and downloaded byte readback / SHA256 checks, no modification of any historical original, and non-execute DRY_RUN default.

**9/9 offline regression tests PASS**: valid absent file, target symlink, ancestor symlink, non-directory ancestor, root symlink, unsafe source paths, invalid ref, existing manifest fail-closed, dry-run no writes. A separate actual matrix DRY_RUN returned 5 races, 24 indexed source files, writes 0.

**Operator package** `boat_edge_p0_hardened_preserver_20261104.zip`, SHA256 `a1e8bec7d070dc431e23f8fa9b05d36a25bed17bbead0860859685d7c4afb414`, contains new Python source, nine-test suite, and the original 45-batch plan. ZIP CRC passed. **Original historical prediction/result/odds bytes included: 0. New live source files fetched: 0.** The package is for authorized operator review and controlled execution on a trusted network-enabled machine only; do not mistake it for a backup.

**Residual note:** Path checks are not an atomic defense against a malicious concurrent process changing ancestors between preflight and file open; run in a protected dedicated directory with no untrusted writers. Do not use this unreviewed script to operate unattended production jobs. Complete independent off-service restoration checks remain essential.

No old-site workflow, predictions, results, odds, Pages, CI, UI or other team's code was changed. **DELETE_BLOCKED / LEGACY_WRITER_STOP_BLOCKED.**
