# P0 raw-original acceptance gate — 5,578 indexed files (2026-11-04 JST)

This is a fail-closed **local read-only verification toolkit**, not a historical forecast backup or an authorization to stop legacy systems.

The immutable legacy retention matrix has **1,125 P0 races** and **5,578 indexed source-file references** across prediction snapshots, audit, histories, odds, and results. Each indexed file needs separately verified original bytes. The 46 absent odds references and one absent history reference remain explicitly **not indexed**; they must not be synthesized.

A standalone verifier `verify_p0_full_originals_20261104.py` and its test suite were prepared offline. It checks a local `originals/<pinned_git_tree>/data/...json` mirror for each expected source; independently computes Git blob SHA1 and local SHA256; rejects missing, modified, symlinked, path-traversing or duplicate inputs; and **fails closed** until all 5,578 indexed files match. It does not edit the source tree, change the predictions, or claim an external/off-host receipt.

**Tested:** 9/9 unit tests PASS. In a test temporary directory containing only the *actually previously retrieved original* Kiryu 5R odds JSON (2,898 bytes; SHA256 `e49b68d44f27bc7cc22bc7f471a76b1372f97dbaa3925727359fe2406d28757c`), the verifier returned **1 SOURCE_BLOB_MATCH / 5,577 NOT_PRESENT**, and **all_indexed_originals_match=false**. This validates that a sample does not accidentally pass the cohort retirement gate.

Operator downloadable toolkit ZIP: `boat_edge_p0_5578_originals_acceptance_20261104.zip`, ZIP SHA256 `722fba5475c74bc05991f6ec9fadcb887a18077a63613f6d0ba812855bfcc1e5`. Contains original matrix, verifier, tests and manifest, **no original forecast/odds bytes**. Source cross-service transfer was previously blocked and was not retried via another route.

**No production changes; no merge; DELETE_BLOCKED / LEGACY_WRITER_STOP_BLOCKED.**
