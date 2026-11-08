# 2026-11-08 ~21:18 JST — official 2-original raw-byte recheck, frozen-forecast chronology, 8-day schedule trend

**Audit-only Draft PR #1694. Not formal T−12 certification, not a model/collector repair.** No main, production, original artifacts or previous forecast bytes edited.

## 1. Replayed original ZIP files, 2026-11-05 to 2026-11-08

All five checked ZIP artifacts passed ZIP CRC; their whole ZIP SHA256 matched their advertised GitHub artifact digests. In the four nonempty official-pair samples, **14 original-source manifest files** had matching original-byte SHA256 and byte lengths. The independently re-audited per-race summary, copied from original JSON manifests and 120-way odds contents, is:

| UTC/JST day | GitHub run / artifact | Race | Official T−12 | Last original receipt (JST) | Six exhibition times/tilt/ST + 120 unique odds | Research-only verdict |
|---|---|---|---|---|---|---|
| 11/05 | [#41976534374](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/41976534374) / 13391673467 | **びわこ11R `202611051111`** | 14:54 | 14:50:58.419703 | **6/6, 6/6, 6/6, 120/120** | pair complete |
| 11/05 | same | `202611052210` | 15:00 | 14:51:17.019665 | **0/6 exhibition**, ST not complete, odds 120/120 | incomplete |
| 11/06 | [#42170457446](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42170457446) / 13480945699 | `202611060810` | 10:42 | 14:47:28.059302 beforeinfo only | after cutoff; no odds original | incomplete/late |
| 11/06 | same | **鳴門10R `202611061410`** | 14:53 | 14:47:48.721444 | **6/6, 6/6, 6/6, 120/120** | pair complete |
| 11/07 | [#42342115412](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42342115412) / 13561893314 | `202611071409` | 14:22 | 14:18:08.824106 beforeinfo only | **0/6 exhibition**, 4/6 tilt, no odds original | incomplete |
| 11/07 | same | `202611071110` | 14:34 | 14:18:38.847534 | **0/6 exhibition**, odds 120/120 | incomplete |
| 11/08 | [#42450048245](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42450048245) / 13604969020 | **江戸川9R `202611080309`** | 14:18 | 14:15:48.378360 | **6/6, 6/6, 6/6, 120/120** | pair complete |
| 11/08 | same | `202611081409` | 14:22 | 14:16:07.127274 | **0/6 exhibition**, ST not complete, odds 120/120 | incomplete |
| 11/08 20:59 | [#42478155155](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42478155155) / 13616706001 | no races selected | — | — | 0 candidates; 0 originals | green no-op, not a capture |

Archive ZIP SHA256s (full, from real GitHub-provided artifacts, checked against local ZIP bytes):
- Nov05 13391673467: `cdd941d41d43adcadbbc24224a94654ec76962616dd16ea995506a3fb8b670ce`
- Nov06 13480945699: `f6e167d79648bb67ec0a3727cc61272291ba00b11c67fad9a186c281e5db89c1`
- Nov07 13561893314: `730f703cb24599a6ef94de3c6e314f54d3f07110265e453794e0d64d38b1323f`
- Nov08 13604969020: `2bda1f350f18d7516ae685fd6a10094915fa00ae6cd8f3f3151b4bef651d2a5c`
- Nov08 20:59 13616706001: `d08493e016e6d0f5060d2b357942a86a32a4c2e59f712c109b9be9d1f7a4345d`

Totals across those four selected original-capture runs: **8 source-pair attempts, 3 verified complete two-original pairs, 5 incomplete**, no official racelist third original. The 20:59 run is a separate zero-candidate observation, not a failed pair attempt. These are selected actual runs, not the denominator for *all* races and not a representative accuracy sample.

## 2. Immutable forecast chronology, identical race codes

Forecast records were fetched from **unchanged main commit** `6b371040fd2fc4398bfa882e6557c333cc0800c8`, not regenerated. Their original creation times are not retroactively changed by later source observation.

| Race | CLEAN original generation | V2 four-mode original generation | Last official 2-source receipt | Why all frozen predictions fail |
|---|---|---|---|---|
| びわこ11R 11/05 | 11:04:24.496897 | 11:15:10.119704 | **14:50:58.419703** | CLEAN **3h46m33.923s** too early; V2 **3h35m48.300s** early |
| 鳴門10R 11/06 | 10:15:39.642861 | 10:15:36.394911 | **14:47:48.721444** | CLEAN **4h32m09.079s** too early; V2 **4h32m12.327s** early |
| 江戸川9R 11/08 | 10:12:31.149675 | 10:17:12.313648 | **14:15:48.378360** | CLEAN **4h03m17.229s** too early; V2 **3h58m36.065s** early |

Every CLEAN prospective file marks `input_source_kind=public_pre_race_csv` and `attestation=pending Git remote first-add verification`. Every original V2 four-mode snapshot has `beforeinfo=optional_not_in_snapshot`. **Neither original prediction is demonstrated to consume these later official originals.** Even if first Git remote acceptance were separately observed, it could not retroactively fix this reversed source→generation order. A *newly generated, prospectively frozen* prediction is required. The independent Git first remote receipt and final entry gates remain unresolved.

## 3. Official-pair collector schedule trend is not a one-day anomaly

The current main collector workflow `.github/workflows/research-live-preview-evidence.yml` declares `*/5 0-12 * * *` (156 nominal slots **per completed UTC/JST racing day**). Direct GitHub schedule-event API date-scoped inventories for 2026-11-01…11-08 returned complete single pages (all total_count < 100).

| Day | Observed event=schedule runs | Run creations during UTC 00–12 declared hours | Creations outside UTC 00–12 |
|---|---:|---:|---:|
| 11/01 | 3 | 2 | 1 |
| 11/02 | 2 | 1 | 1 |
| 11/03 | 2 | 1 | 1 |
| 11/04 | 2 | 1 | 1 |
| 11/05 | 2 | 1 | 1 |
| 11/06 | 2 | 1 | 1 |
| 11/07 | 3 | 2 | 1 |
| 11/08 (partial watch) | 2 | 2 | 0 |

For **seven completed days 11/01–11/07**: 16 observed run creations in total against 1,092 nominal five-minute slots; just 9 creations within declared UTC 00–12 hours. **This is an invocation-count discrepancy, not 1,076 proven skipped HTTP fetches or 1,083 identifiably missed exact cron slots.** The 7 outside-hours creations could reflect delayed schedule events; no root cause has been proven from metadata alone. The fact that this pattern predates the Nov 4 commit `a5cb6670064af916171b677a466c710e5b81f44f` (which added official source-pair capture to this workflow) makes it unsafe to assign the long-term activation deficit to the Nov 4 source-pair addition.

## 4. Decision and handoff

- **Auditor:** The original-source pair pipeline has **three proven research-only positive pairs**, proving it *sometimes* works. Do not label them formal, claim model lift, or add them to a formal accuracy denominator. Keep their exact ZIP hashes/artifact IDs and immutable forecast creation times separately inspectable.
- **Source owner ①:** Determine why an intended 5-minute schedule produces only 2–3 daily recorded creations over an eight-day window; distinguish GitHub activation, missed cron, concurrency, actual HTTP errors and green empty jobs. Fix collection in its own scoped Draft PR. Preserve the **third** official racelist original and final 6-entry provenance for the same race. Prove actual model consumption from replayed official originals.
- **Independent first-add owner:** Establish GitHub remote acceptance evidence independent of local Git author/committer time and self-reported timestamps, strictly **after** official sources were collected but **before** T−12. No result-contaminated backfills or overwrite of earlier frozen forecasts.
- **No production release, main merge, automatic merge or formal accuracy promotion** until each gate passes prospectively. Final formal T−12 **0**, denominator **undefined**.

Regression: the independent two-original/frozen diagnostic now includes real archived 11/05 Biwako and 11/06 Naruto chronology fixtures alongside 11/08 Edogawa, and checks V2 never silently assumes official beforeinfo. These test fixtures validate the rule; **the ZIP byte reinspection above is a separate real-data audit**.
