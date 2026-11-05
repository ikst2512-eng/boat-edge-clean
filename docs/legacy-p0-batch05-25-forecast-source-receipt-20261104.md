# P0 batch 05: 25 legacy forecast original-source Git receipts (2026-11-04 JST)

Read-only review; this **does not back up source bytes to independent custody** or authorize retiring any system. Scope: frozen race-retention matrix P0 rows 101–125 (0-based indices 100–124), legacy repository `ikst2512-eng/boat-edge` pinned tree `f38204105a979aa6ef5293d1b9cad854056faadd`.

For each of the 25 race codes below, an authenticated GitHub `fetch_file` read actually fetched `data/site_prediction_snapshots/YYYYMMDD-NN-NN.json` at the pinned commit. Each was valid JSON with exact `race_key=YYYYMMDD-NN-NN` and `prediction_kind=SITE_REFERENCE_V122`. The GitHub-returned content blob SHA1 matched the separately frozen `prediction_snapshot_blob_sha` field in `boat_edge_legacy_retention_race_matrix_20261104.csv` for **25/25**; **0 missing / 0 metadata mismatch**. These are GitHub-returned source Git blob identities; this exercise did *not* independently calculate a Git blob SHA1 from unmodified raw binary bytes or a restored SHA256.

| P0 race code | Expected and returned Git blob SHA1 |
|---|---|
| 202610082003 | `bfefa9b4f313e4c0dd6065f700561f0ab96e06e0` |
| 202610082005 | `43131ed42d1ffc6fbaec0c80f204ce4cc92b5f48` |
| 202610082006 | `00fd95391964a8c0a01143eefa55fd0b84986031` |
| 202610082007 | `1db7d5e6dd5dc39659e4d0428463399ad3fbb2f1` |
| 202610082008 | `a98c77d97d3ad453f7f80f023137d0f5f6d579a3` |
| 202610082009 | `a14be060671156301c44b747408d9aac5f19f0c8` |
| 202610082010 | `8be1e0ee98a3ed7edf5eeb75b6571e5b17c41a78` |
| 202610082011 | `6672e7da649980c6c3817f87b62e223a94554adc` |
| 202610082012 | `a07f536837781f468bd38bcad112efc52d7c2c2e` |
| 202610082301 | `f21d59562ee66a772d43ba0d14e0357e94c6ec2f` |
| 202610082302 | `1a03a1dc0b43e619a2ed4301154cd1e16eaa3b4a` |
| 202610082305 | `057d47552b468916c34493a6421f85be93ec77a5` |
| 202610082306 | `ca87499085a0b4bd9c055ed5e60dd15dd5538d76` |
| 202610082307 | `02acd08dbcdf6d1e7cf66596d9419774282ad1f4` |
| 202610082308 | `8961540c17d3bbf29d7d459c349a34b0c4eb7586` |
| 202610082310 | `e45ace26e5f2f9cc1397d1a8e4eb673b6236a595` |
| 202610082311 | `88d16b46fa066113737e1a938dc09b4d9351f9b0` |
| 202610082312 | `4c997bd2d295ba4a75f831346db88893c4f49d04` |
| 202610082401 | `1dd819887aaafef7418a99266c0f17108f7d53c4` |
| 202610082402 | `2eed33f1d4c549479f62cf1d2613101f90fc25bb` |
| 202610082403 | `cfb196741bd3df922ef25c9f8403941245d7cf05` |
| 202610082404 | `51283eb093b844b2362fd5821357d18b40ead3de` |
| 202610082405 | `089763eef30ef53e3094e981e33bc5633d77137c` |
| 202610082406 | `02c56da30ca70da685835b0eb6ff5c52d2bc20f0` |
| 202610082407 | `3e536a6ea5bc0ac93f114f132101cafd4edf719d` |

Prior independently documented P0 batches 01–04 directly checked **469 indexed objects across 100 races**. This new batch checks **25 previously unchecked source paths across 25 distinct races**, bringing distinct directly confirmed GitHub source-file identities to **494 indexed objects across at least 125 races**. Note: the remaining four source categories for batch 05 are *not* checked here, so this is not a fully verified batch of 125 objects.

**Independent custody is unchanged: just 1 of 5,578 P0 original source files has separately verified offsite restore.** The earlier 412 independently restored result originals belong to P1/P2, not P0. No old predictions, immutable source files, Actions, web Pages, CLEAN main, or other teams' code changed. Do not claim a P0 backup exists. `DELETE_BLOCKED / LEGACY_WRITER_STOP_BLOCKED`. Keep Draft PR #1559 unmerged.
