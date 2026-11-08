# Independent T−12 audit — original ZIP replay, Nov 5–8 2026

**Audit-only.** This is a real, bounded, source-level replay of five Actions ZIP artifacts, not a synthetic CI cohort, not a formal T−12 prediction result and not a claim that all historical or unscheduled runs were covered. The saved original bytes, source manifest SHA256/length/identity, official beforeinfo deadline, six exhibition times, six tilts, six exhibition ST/course rows and **120 distinct valid 3T trifecta permutations** were independently checked with Python HTML DOM/JSON parsing. ZIP CRCs all pass, and each downloaded ZIP SHA256 matches its GitHub Actions artifact digest.

## Replayed official pair evidence

| Date | Race and status | Official T−12 / receipt of last required original (JST) | Official beforeinfo | Official odds3t |
|---|---|---|---|---|
| Nov 5 | **`202611051111` びわこ11R — pair COMPLETE** | **14:54:00 / 14:50:58.419703** (181.580 s remaining) | 6 exhibition + 6 tilt + 6 ST/course | **120/120 unique** |
| Nov 5 | `202611052210` 福岡10R — incomplete | 15:00:00 / 14:51:17.019665 odds | **0/6 exhibition, 0/6 ST/course** | 120/120 |
| Nov 6 | `202611060810` 常滑10R — late/unpaired | **10:42:00 / 14:47:28.059302** beforeinfo (over four hours late) | **0/6 exhibition, 0/6 ST/course** | No archived odds original |
| Nov 6 | **`202611061410` 鳴門10R — pair COMPLETE** | **14:53:00 / 14:47:48.721444** (311.279 s remaining) | 6 exhibition + 6 tilt + 6 ST/course | **120/120 unique** |
| Nov 7 | `202611071409` 鳴門9R — odds failed | 14:22:00 / 14:18:08.824106 beforeinfo | **0/6 exhibition, 0/6 ST/course**, 4/6 tilt | No successful odds original (`official_odds_probe_failed`, ValueError) |
| Nov 7 | `202611071110` びわこ10R — incomplete | 14:34:00 / 14:18:38.847534 odds | **0/6 exhibition, 0/6 ST/course** | 120/120 |
| Nov 8 | **`202611080309` 江戸川9R — pair COMPLETE** | **14:18:00 / 14:15:48.378360** (131.622 s remaining) | 6 exhibition + 6 tilt + 6 ST/course | **120/120 unique** |
| Nov 8 | `202611081409` 鳴門9R — incomplete | 14:22:00 / 14:16:07.127274 odds | **0/6 exhibition, 0/6 ST/course** | 120/120 |

**Aggregate on these 8 real race attempts:** **3** verified, complete pre-T−12 *official two-original pairs*, **5** incomplete/late/failed; **0** formal T−12 certificates. `beforeinfo.json` is present for all eight; official odds HTML for six; **no official racelist HTML is present in any of these five ZIPs**. The Nov 8 20:59 green scheduled run [#42478155155](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42478155155) returned `status=no_pre_t12_candidate`, `eligible_candidates=0`, `beforeinfo_originals_saved=0`, `official_odds_originals_saved=0`. It must count as an **invocation**, not a successful source-pair capture or a formal candidate.

**Pinned Action ZIP originals** (all SHA256 and CRC verified):

| Scheduled run | Date, status | Artifact ID / exact ZIP SHA256 |
|---|---|---|
| [#41976534374](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/41976534374) | Nov 5, 1 pair | `13391673467` / `cdd941d41d43adcadbbc24224a94654ec76962616dd16ea995506a3fb8b670ce` |
| [#42170457446](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42170457446) | Nov 6, 1 pair | `13480945699` / `f6e167d79648bb67ec0a3727cc61272291ba00b11c67fad9a186c281e5db89c1` |
| [#42342115412](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42342115412) | Nov 7, 0 pairs / source failure | `13561893314` / `730f703cb24599a6ef94de3c6e314f54d3f07110265e453794e0d64d38b1323f` |
| [#42450048245](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42450048245) | Nov 8 14:15, 1 pair | `13604969020` / `2bda1f350f18d7516ae685fd6a10094915fa00ae6cd8f3f3151b4bef651d2a5c` |
| [#42478155155](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42478155155) | Nov 8 20:59, 0 candidates | `13616706001` / `d08493e016e6d0f5060d2b357942a86a32a4c2e59f712c109b9be9d1f7a4345d` |

**Source manifest SHA256 for successful pairs** (beforeinfo / original odds HTML):
- `202611051111`: `38aa13958010655cb9851270c423aa078a6318d648b34f730d5b92a12b86ee07` / `c11d231a4d386fdac146ab7a5f548ac6d3dafe67096ff6cfbeec294f2683196d`
- `202611061410`: `8fc561b85b00cdbe8072b155500e6306e10f4d4a3143e5b7c89135eed37b8d38` / `3d547d9acd4df3d37e0277b5bbbce34fb528052de2ab0b2734e928f0ad2092fe`
- `202611080309`: `b52b2e8e400ee00676c247007576abd21be4ed64307e0b2cbafa159c51662db5` / `9ce8d53029bd9022743599de1e7f670439d20efad35f52546d8a99f6347a7aab`

## Frozen prediction chronology directly verified against main

The existing **frozen CLEAN** and **four-mode V2** Git files for each of the three successful source pairs were fetched independently from main. Every relevant generation timestamp predates its race's official 2-source receipts; there is no supported source-consumption link to the later original HTML/JSON:

| Race | Frozen CLEAN generation JST / source | Frozen V2 generation JST / beforeinfo | Last official receipt JST |
|---|---|---|---|
| びわこ11R Nov 5 | **11:04:24.496897** / `public_pre_race_csv` | **11:15:10.119704** / `optional_not_in_snapshot` | **14:50:58.419703** |
| 鳴門10R Nov 6 | **10:15:39.642861** / `public_pre_race_csv` | **10:15:36.394911** / `optional_not_in_snapshot` | **14:47:48.721444** |
| 江戸川9R Nov 8 | **10:12:31.149675** / `public_pre_race_csv` | **10:17:12.313648** / `optional_not_in_snapshot` | **14:15:48.378360** |

All six existing forecast files are **ineligible for retrospective promotion**. The available source-receipt-to-official-T−12 margins for a *new* forecast were **3m01.580s, 5m11.279s and 2m11.622s** respectively. Owner ① needs to generate *fresh* forecasts after those originals, prove the actual bytes were consumed, and independently attest initial remote GitHub acceptance before that narrow cutoff. No past forecast timestamp may be substituted.

## Scheduling investigation — not a Nov 8-only regression

Queried full `event=schedule` API pages for Nov 1–8 (all daily response counts below 100, no pagination truncation) and isolated the exact workflow file `research-live-preview-evidence.yml`. Observed run **creation counts by UTC day**: Nov 1 **3**, Nov 2 **2**, Nov 3 **2**, Nov 4 **2**, Nov 5 **2**, Nov 6 **2**, Nov 7 **3**, Nov 8 **2** by 20:59 JST. GitHub cron config `*/5 0-12 * * *` nominally schedules **156 UTC slots/day**. This sparse recorded schedule event volume was already present earlier than Nov 8; there is **no basis to attribute its onset to Nov 8**. Some runs were created outside the cron's nominal UTC hours and could have been delayed; metadata alone does not prove precise per-slot trigger identity or explain GitHub's scheduling behavior. The official pair capture step was introduced to this pre-existing workflow by main commit `a5cb6670064af916171b677a466c710e5b81f44f` on Nov 4 20:25 JST; Nov 1–early Nov 4 workflow starts cannot be misclassified as official pair acquisition.

For the **four post-introduction JST production days** Nov 5–8, observed creations were **2 / 2 / 3 / 2**, with actual at-least-once complete source-pair research observations on Nov 5, Nov 6 and Nov 8, not Nov 7. Distinguish those historical partial successes from the persistent missing schedule/three-source/forecast lineage. All original raw successes came through **Actions artifacts**, whereas the distinct durable Git original-trio branch `research-t12-external-evidence` still had **no Nov 8 folder** on immutable SHA `d0ed89f146dff117021c2bc042b20259d6715515`.

## Operational handoff priorities

1. **① Structural blocker:** dedicated official-three-original observation workflow is manual-only; the repeating research workflow collects **beforeinfo+odds**, not **racelist**. Instrument an actual same-race *three-original* pre-T−12 acquisition + immutable storage path in ①, not in audit PR #1694.
2. **① Activation reliability:** actual `event=schedule` creation sparse consistently since before Nov 5. Distinguish missing/delayed workflow triggers from source HTTP responses. A green run with zero eligible races is a **no-op**, not proof of source recovery. Independently inspect 403/404/Timeout rather than accepting them.
3. **① Prospective forecast linkage:** the existing 2-source success left only **~2–5 minutes** until T−12. New prediction must consume independently verified official originals and be frozen and remotely witnessed before cutoff. Do not rewrite earlier morning CSV forecasts.
4. **Auditor:** verify official racecard/registration identity and final entry, actual source consumption, Git first-add/remote timestamp and exact archive bytes before permitting any formal certificate. Remain **formal=0; accuracy denominator undefined**.

**Boundaries:** No main merge/auto-merge. No collector, schedule, model, UI, Render, or existing forecast files edited. This report and the pair ZIP replay are research-only evidence.
