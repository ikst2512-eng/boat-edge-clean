# P0 original snapshots: all 46 missing-odds-reference cases verified (2026-11-04 JST)

**Direct-source verification; no historical source editing.** Continuing Issue #708/#329 and Draft PR #1559.

## New finding

Every one of the 46 P0 legacy-only race IDs classified as `ODDS_NOT_INDEXED` was directly fetched through the GitHub connector as `data/site_prediction_snapshots/{race}.json` at the fixed legacy commit `f38204105a979aa6ef5293d1b9cad854056faadd`. **46/46 fetches succeeded and 46/46 parsed JSON documents have `odds_sha256: null`.** This is broader, direct source verification, replacing the earlier partial six-sample observation. No failures or non-null `odds_sha256` in this cohort.

By race date: 2026-10-08 **36**, 2026-10-09 **9**, 2026-10-10 **1**.

A 46-row local CSV receipt `boat_edge_p0_46_odds_null_verified_20261104.csv`, SHA256 `8ceb2190fe451b2c521fcf3a615feae149138043c98cb1acf7b7e9ade71b06b5`, records source path, pinned Git tree, source blob SHA from the prior index, inspection status, and **UNVERIFIED** for alternative provenance and independent backup. This CSV contains **no original snapshot bytes**.

## Evidentiary interpretation

1. The source prediction has **no immutable odds SHA linkage** in each of these 46 archived snapshots. This is not the same as `SHA_MISMATCH` (corrected earlier for three *other* races), nor does it prove that absolutely no odds file existed at an alternate path, in an older Git tree, or as an external source.
2. Later odds files, reconstructed historical prices and results must **never** be attached post hoc as the original forecast-time odds input.
3. None of these 46 snapshots can pass an evidence gate requiring a stored cryptographic odds original link **without additional independently preserved contemporaneous evidence**. They remain `ODDS_PROVENANCE_UNVERIFIED`, not retroactively `formal Fresh` and not approved to enter strict odds-dependent scoring.
4. The separate **one history-reference absence** is `20261008-14-05` (Naruto 5R); its result is `trifecta_not_established`, so retain it without inventing 3T outcome or payout.

## Outstanding

The 46 first Git-add proofs, alternate historical odds paths, and the original bytes' replicated non-expiring backup plus restored SHA256 have **not** been completed. All 1,125 P0 source originals still require that independent durability evidence. No deletion, stop, migration or model promotion authorized.

**DELETE_BLOCKED / LEGACY_WRITER_STOP_BLOCKED.**
