# T−12 same-race five-gate status — 9 November 2026, read-only follow-up

Scope: Draft #1694 only. This report distinguishes **three fixed historical races** from all possible racing-day observations. No production source acquisition, model, schedule, UI, or main change.

## New actual CI observation outside the three-race original cohort

At **2026-11-09 21:46 JST**, [scheduled current-day beforeinfo probe #42619773299](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42619773299) concluded **failure** on main `4bd080ad77778053575cf497c8a6b85b959ce173`. Its actual probe job logs reported:

- `tkz` **132 rows**, `eligible_future=0`;
- `stt` **132 rows**, `eligible_future=0`;
- `sui` **132 rows**, `eligible_future=0`;
- `MATCHED_CURRENT_PREDEADLINE 0`, `ADAPTER_VERIFIED_CURRENT_PREDEADLINE 0`;
- terminal `RuntimeError: SCHEDULED_PREVIEW_NO_MATCHED_PREDEADLINE_RACES`.

This means **no predeadline candidate remained at the observation time**. It does **not** prove an official boatrace HTTP outage, an invalid official exhibition record, or new complete official T−12 evidence. No retrospective late observation may be counted.

## Exactly three archived original-source race cases

The existing independent same-race proof chain replayed the Nov 3 original Git blobs and Nov 9 actual source artifact + immutable existing forecasts. To support the explicit **five-condition** request without creating a duplicate replay implementation, the existing `scripts/audit_t12_same_race_proof_chain.py` now summarizes those already-verified per-race booleans.

| Five evidence gates for the fixed historical cohort | Verified of 3 races |
|---|---:|
| Beforeinfo and complete six-boat exhibition | **2/3** |
| Official 120-way trifecta odds original | **3/3** |
| Recorded official deadline/T−12 source cutoff ordering | **3/3** |
| Genuinely generated forecast *after* the same-race originals and before T−12 | **0/3** |
| Independently evidenced first forecast Git remote acceptance | **0/3** |

Additional independent prerequisites are separately retained: matching official racelist raw original **1/3**; independently replayed model consumption of original bytes **0/3**; final official race entry independently verified **0/3**. A cutoff comparison does not independently establish source receipt or model use; authenticated **source ZIP** creation is not first **forecast Git** acceptance.

- **202611030112 桐生12R:** three official source filenames + 120 odds, but no valid six-boat exhibition (0/6); no acceptable model lineage.
- **202611091710 宮島10R:** six-boat beforeinfo and 120 odds before cutoff, but no third racelist original; original CLEAN/V2 forecasts were generated before those official receipts.
- **202611091110 びわこ10R:** same blockers as 宮島10R.

**All five same-race gates satisfied: 0/3 historical cases. Fully qualified three-original sources: 0. New certified T−12 forecasts: 0. Formal forecast-accuracy denominator: undefined, NOT three.**

Historical scope stays frozen and results may not be recombined across races. New fully sourced observations must come via the separate collector owner, with independent raw-byte replay and first Git remote proof.

## Adjacent Draft PR scope

[Draft #1709](https://github.com/ikst2512-eng/boat-edge-clean/pull/1709) removes obsolete **dated** workflow definitions only. Its passing PR-only test does not mean those changes are in main. #1694 intentionally pins the full 149/51 workflow audit to immutable main `4bd080ad77778053575cf497c8a6b85b959ce173`. If #1709 is ever manually merged, recompute current-tree counts separately rather than silently changing this historical denominator. Do not remove original research scripts or receipt archives from #1694.

Review only: #1694 Draft, no main automatic integration; #1699 owns recurring trigger monitoring. No formal accuracy promotion.
