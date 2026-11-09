# 2026-11-09 19:36 JST — same-race T−12 proof-chain audit, three REAL races

**Independent audit only:** Draft PR #1694; no change to main/collector/model/cron/Render/UI/previous forecast files. Formal certified T−12 forecasts **0**, accuracy denominator **undefined**, no formal hit-rate improvement claim.

## New guarded result: archived components from DIFFERENT races cannot be combined

A new independent fail-closed step consumes **three prior independently verified real-source reports**, never a fabricated or self-declared source-success field:

1. `reports/official_t12_nov03_pinned_three_originals.json`, created from actual six original/manifest Git blobs pinned to evidence branch commit `d0ed89f146dff117021c2bc042b20259d6715515`. Race `202611030112`, 桐生12R. Official racelist 6 identities, beforeinfo 6 racer rows, 120-way odds complete, **but exhibition times 0/6, tilts 0/6, exhibition ST 0/6 and exhibition courses 0/6**. Three filenames do NOT establish a qualified T−12 source triad.
2. `reports/official_t12_nov09_source_vs_forecast.json`, created by actual source-byte/manifest replay of GitHub original Actions artifact `13652131213` (source schedule run `42567310743`), plus exact pinned forecast Git blobs for 宮島10R `202611091710` and びわこ10R `202611091110`. Both races: **official beforeinfo 6/6 and 120/120 odds**, **official racelist original absent from this archive**, and **four CLEAN/V2 predictions were frozen before the official originals arrived**.
3. `reports/official_t12_nov09_remote_archive_time.json`, independently fetched GitHub Actions run & artifact server timestamps, exactly matched source run/artifact/digest and race/cutoff/last original receipt. Both Nov9 official pair ZIPs were published by GitHub at **14:27:00 JST**, preceding official T−12 cutoffs for 宮島10R 14:28 (60s margin) and びわこ10R 14:30 (180s margin). The archive server timestamp is NOT the model forecast's first Git remote receipt.

These reports are read-only generated from actual GitHub sources **by the same exact CI run**. All source and forecast original bytes were separately replayed in upstream workflow steps before joining. The join checks exact race code, same JST day, source cutoff, replay flags, authenticated archive identity and missing-field agreements for every row; it refuses an attempt to borrow the Nov3 racelist to cover Nov9, to borrow Nov9 exhibition to make Nov3 valid, to borrow archive times across races, or to count a post-hoc frozen forecast.

| Historical race | Official racelist original | Complete six-lane exhibition | Complete odds original | Source archive GitHub remote-before-T−12 timestamp | Post-official-source forecast | Qualified same-race official triad |
|---|---|---|---|---|---|---|
| 桐生12R Nov3 | **Yes** | **No** | **Yes** | Not independently established | No proven eligible forecast | **No** |
| 宮島10R Nov9 | **No** | **Yes** | **Yes** | **Yes** (source ZIP, not forecast) | **No** (earlier CLEAN/V2 files only) | **No** |
| びわこ10R Nov9 | **No** | **Yes** | **Yes** | **Yes** (source ZIP, not forecast) | **No** (earlier CLEAN/V2 files only) | **No** |

**Bounded metrics: 3 distinct historical races inspected, 1 archived three-original filename set, 2 complete official 2-source exhibition/odds sets, 2 source ZIPs published by the GitHub server before official T−12, 0 fully qualified same-race triads, 0 verified post-source predictions, 0 formal certification.** These selected three observations are not the denominator for forecasting performance or a sample of all boat races.

### Code and CI

- `scripts/audit_t12_same_race_proof_chain.py`: compare historical real-original audit results with identity/chronology/nonformal gates, never change source storage.
- `tests/test_audit_t12_same_race_proof_chain.py`: **13 extra regression cases** covering cross-day/cross-race substitution, duplicate race, fabricated triad/exhibition, fake model consumption or first Git receipt, mismatched GitHub artifact-time report, and any formal upgrade.
- `.github/workflows/audit-official-pair-schedule-continuity.yml`: runs tests and a new real report `reports/official_t12_same_race_proof_chain.json` after all upstream source original replays, uploaded as separate read-only audit artifact.

[Exact head CI #42601959246](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42601959246), code SHA `e73541089208919fc2213e2694009b9be9e59157`: **SUCCESS**, **180/180 audit unit tests pass** (previous 167 + 13), actual Nov3 3-source Git SHA replay, Nov5–8 real Actions source ZIP replay, Nov9 2-source ZIP and four frozen forecast replay, Nov9 server archive-time readback and real same-race chain comparison all succeeded. `T12_SAME_RACE_PROOF_CHAIN` emitted `races_compared=3`, `fully_qualified_same_race_three_original_t12_sources=0`, `cross_race_original_combination_allowed=false`, `new_formal_certifications=0`, `formal=false`.

**Important other CI status, not hidden:** The *distinct* `CLEAN prospective independent accuracy checks` workflow was still **failing** at code head `e735410...`; its historical 2026-11-05 local first-add cohort rejects 111 same-second first-commit ambiguities, while 2026-11-09 day-scope local first-add checks pass 107/107. These local successes have `remote_first_seen_verified=false`. Another mixed archive first-add check rejects **1,085/1,548 frozen candidates**; this failure is neither a source ZIP replay error nor a formal accuracy improvement. Do not use the 180/180 independent audit result to claim every workflow is green.

## Live 2026-11-09 at 19:36 JST

Authenticated date-scoped GitHub collector schedule inventory found **1 actual `event=schedule` collector run** so far (`42567310743`, created at 14:26 JST). **128 nominal 5-minute slots** elapsed through 19:35; 1/128 = **0.78%** observed event-creation-to-slot count ratio. This comparison does **not** prove 127 exact skipped cron slots or 127 HTTP failures, and schedule root cause remains unverified. Research original evidence branch remains at `d0ed89...`, containing Nov3, **no Nov9 saved three-original day directory in that specific branch**.

## Owner-specific next action

**Source collection owner ①:** Restore reliable scheduled activation across distinct workflows (the existing peer-workflow control also shows sparse schedule creations), collect official racecard/racelist and ready official beforeinfo exhibition 6/6 and odds 120/120 **on the same race**, all genuinely before official T−12. Creating source ZIPs early enough is possible and demonstrated for Nov9; completing third original and matching exhibition remains the bottleneck. Avoid taking pre-exhibition early Nov3 racelists and combining them with another race's ready exhibition.

**Forecast and independent verification:** Generate a **new immutable forecast** strictly *after* all three original receipts, but *before* T−12, prove actual replayed raw bytes used by the model; independently record first forecast GitHub remote acceptance (not just source ZIP GitHub timestamps), and final declared entries. Retrospective rebranding of early public CSV CLEAN/V2 predictions is prohibited.

**Review only**: keep #1694 Draft, never auto-merge, do not edit main/production or mark success.
