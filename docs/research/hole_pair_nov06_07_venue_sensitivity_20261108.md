# 2026-11-08 Hole pair: fixed Nov 6–7 venue-sensitivity audit (NONFORMAL)

**Scope:** A post-result *diagnostic of previously frozen tickets*, not a new candidate method, deployment, calibration, or confirmatory result. This file contains no selector, collector, workflow, UI, Render, or production change. Never change the original Nov 6/7 selections using any result in this note.

## Frozen input and independent results

- Nov 6: [original run 42156441818, artifact 13475051686](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42156441818); original extracted `research_candidate_freeze.json` SHA-256 `722540fbae1e8160be41d762e0e6bd9bf9345df4762a50d8320571311973e3d2`, 92 frozen, seven officially cancelled Tokoname `202611060806`–`0812` excluded, 85 held/results matched.
- Nov 7: [original run 42356839515, artifact 13567518705](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42356839515); original extracted SHA-256 `9008639d18c9645bfd01276d08f7cef43482b529d972542d6877e0e098ce5408`, 17 frozen and 17 held/results matched.
- The 109 original frozen race IDs are unique. The later Nov 6 87-record repeated upload is **not** added. All retained Top10 lists are the originally frozen three arms, not reconstructed from results. Method SHA-256 remains `ea30508cd899b10336754cfeec69c69c73f18e09fba421016d6cddc69b9cabcb`; original Top5 and all original 1st/2nd pairs stay protected.
- Independent public results: [Nov 6 CSV](https://github.com/BoatraceCSV/boatracecsv.github.io/blob/main/data/results/realtime/2026/11/06.csv), original Git blob `aec272a053e412fcb2c4f517cc3432cbcb5daf7d`; [Nov 7 CSV](https://github.com/BoatraceCSV/boatracecsv.github.io/blob/main/data/results/realtime/2026/11/07.csv), Git blob `661afd5cfff139ed0bb857c2991d0ec8189239cb`. Outcome triples and all 102 ranks rechecked against the original candidate artifact. Earlier race-by-race explanation: [PR #1685 audit comment](https://github.com/ikst2512-eng/boat-edge-clean/pull/1685#issuecomment-6719660370).

## Same-race reference score (102 held races, 13 of 24 venues represented)

| Arm | Top1 | Top3 | Top5 | Top10 | Top10 newly gained | Top10 formerly hit but lost |
|---|---:|---:|---:|---:|---:|---:|
| Original baseline | 2/102 | 6/102 | 12/102 | 19/102 | — | — |
| `same_pair_two_thirds` | 2/102 | 6/102 | 12/102 | 29/102 | 15 | 5 |
| `two_pairs_one_third` | 2/102 | 6/102 | 12/102 | 24/102 | 9 | 4 |

All Top1/3/5 outcomes are necessarily identical by the predeclared Top5-preservation contract; these arms only test Top10 swaps. Two-sided paired McNemar on this exploratory combined set, after Holm adjustment over two candidate-vs-baseline comparisons, gives `p≈0.08278` for same-pair and `p≈0.26685` for distinct-pair. This is NOT a prespecified confirmation; many prior inspections, venue/day selection, shared race structure and alternative exploratory comparisons remain. No proven uplift.

## Venue sensitivity — descriptive only

Venue codes follow the original 12-digit race IDs. Small and uneven sample counts must not be treated as 24-venue evidence or used for venue-specific selection.

| Venue code | Held n | Base Top10 | Same-pair Top10 | Distinct-pair Top10 | Same gained/lost | Distinct gained/lost |
|---|---:|---:|---:|---:|---:|---:|
| 01 | 17 | 3 | 3 | 4 | 1/1 | 2/1 |
| 02 | 6 | 0 | 2 | 1 | 2/0 | 1/0 |
| 03 | 8 | 3 | 4 | 3 | 1/0 | 0/0 |
| 05 | 7 | 0 | 1 | 0 | 1/0 | 0/0 |
| 10 | 3 | 0 | 0 | 0 | 0/0 | 0/0 |
| 11 | 7 | 2 | 1 | 1 | 0/1 | 0/1 |
| 12 | 18 | 7 | 9 | 8 | 4/2 | 2/1 |
| 14 | 8 | 1 | 2 | 2 | 1/0 | 1/0 |
| 15 | 8 | 0 | 1 | 0 | 1/0 | 0/0 |
| 17 | 6 | 1 | 1 | 0 | 1/1 | 0/1 |
| 19 | 6 | 0 | 2 | 1 | 2/0 | 1/0 |
| 22 | 5 | 1 | 1 | 2 | 0/0 | 1/0 |
| 23 | 3 | 1 | 2 | 2 | 1/0 | 1/0 |
| **Total** | **102** | **19** | **29** | **24** | **15/5** | **9/4** |

Same-pair Top10 net delta is positive in eight represented venues, negative in one, unchanged in four. This does **not** establish venue-specific statistical significance. Largest venue sample is only 18 races. Nov 7's second snapshot represents only 17 late races out of 122 original Nov 7 forecasts (105 beyond cutoff); do not extrapolate to a full day.

## Failure mode and bias

- Original baseline missed the exact Top10 in 83/102: winning first boat absent **11**, first–second pair absent **56**, winning third boat absent despite pair coverage **16**. These are mutually exclusive hierarchical attribution buckets.
- All 15 same-pair Top10 gains were previously missing the **winning first–second pair** and had winning order **`1-2-3` (9)** or **`1-2-4` (6)**. The 15 gains occur across 10 venue codes; the policy's added tickets are strongly concentrated in these two triples. This is evidence of a narrow exposure mechanism, NOT a general correction for all pair misses.
- All five same-pair Top10 losses, and all four distinct-pair losses, retain the original winning first–second pair but replace its exact correct third choice. Do not fit a new third-choice exception from these known outcomes.
- In the **post-result-defined** 17/102 races won by `1-2-3` or `1-2-4`, same-pair finds 15 and baseline 0; on the remaining 85, the baseline finds 19 and same-pair finds 14. This subgroup is purely explanatory; it must never become a new predictor or serve as confirmatory evidence.

## November 8 and prospective boundary

- Latest reviewed main `6b371040fd2fc4398bfa882e6557c333cc0800c8` (committed 2026-11-08 17:47:24 JST) has 116 Nov 8 original 4-mode forecasts and 111 Nov 8 saved result files, **not** proof of 116 pre-result #1685 pair candidates. The inspected latest research PR CI [run 42461525238](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42461525238) produced a **readiness-only** artifact and no candidate freeze; no verified Nov 8 pair-policy accuracy denominator is added.
- Nov 9+ [original registered pilot/confirmation protocol](https://github.com/ikst2512-eng/boat-edge-clean/blob/research/hole-pair-future-precommit-20261105/research/hole_pair_future_holdout_protocol_20261109.json): first 300 eligible records pilot, next untouched 300 confirmation; keep policy, hash, two-comparison Holm guard and no selection by outcomes. An independent first-acceptance timestamp, official pre-T−12 full six-boat beforeinfo/exhibition plus 120 odds and independently saved results are prerequisites; unverified, missing, late or cancelled records must be accounted for separately, not forced into the denominator.
- Draft receiver is **not deployed**; formally evidenced candidate first receipts = 0, formally confirmed efficacy = 0; `formal=false`, `production_promotion_allowed=false`. Do not merge automatically or modify main, model, collector, schedules, production forecasts, UI or Render. Separate #1688 historical 106 and #1693 all-four-mode cohorts must not be added.
