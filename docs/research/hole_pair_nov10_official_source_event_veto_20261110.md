# 2026-11-10 — fail-closed official source event handoff VETO (nonformal)

**Status:** read-only research on Draft #1685, **not a production trigger or official data collector**. No main, Render, Cloudflare, D1 receiver or forecast method modifications. This does not change frozen hole-pair baseline/Top1/3/5/10 or the 600-race formal cohort.

## Motivating real-source issue

The pinned actual main forecast source tree at `c4d39245cbc96b6c680585a68c3b9adf6ddeb921` contained exactly **150** Nov 10 Git-blob-verified forecast originals. All **150** original JSONs had `beforeinfo=optional_not_in_snapshot`, and no independent #1694 official-original handoff packets were attached to the #1685 candidate-freeze inputs.

The separate [#1694 historical proof chain](https://github.com/ikst2512-eng/boat-edge-clean/blob/audit/t12-nov06-day-isolation-20261106/docs/audits/t12-independent-nov09-2146-five-gate-and-postdeadline-probe.md) proves why **two original source artifacts alone** are insufficient: fixed Nov 9 宮島10R and びわこ10R had 6/6 exhibition rows and 120-way odds before T−12, but *lacked same-race official racelist originals*, and their pinned forecasts predated original source acquisition. The fixed Nov 3 桐生12R had all three original filenames but **0/6 complete exhibition**. These are historical source counterexamples, **not** eligible prospective Nov 10 hole-pair observations. No races in those source audits had independent first *forecast* acceptance.

The goal in this Draft is to make premature **gate admission** visible and testable, without inventing an authoritative source signature or a live receiver.

## Implementation

New `research/hole_pair_official_event_veto_audit.py` consumes the **existing** validated `research/hole_pair_real_main_snapshot_gate.py` 150-row output, using the existing fail-closed `checked_rows` validation, and optionally a **caller-supplied, untrusted** per-race #1694-style handoff claim. It does not duplicate the official collector or evidence replay code.

The optional claim schema is closed and tied to one 12-digit original race ID. It includes a claimed upstream audit SHA256, last-original receipt (JST), official deadline (JST), claimed raw SHA256 hashes of same-race racelist, beforeinfo and trifecta odds, 0–6 distinct exhibition boats, 0–120 distinct trifecta odds, and an optional GitHub SOURCE archive ID. This is a schema contract for an eventual independently audited handoff; **hash strings and clocks supplied by a caller are NOT accepted as authentic original-source proof.** No client flag can turn this into an authorized event.

For **every original forecast** the audit emits its original declared T−12, elapsed/open classification at the pinned 16:33 JST reference, missing original components, source-after-forecast ordering blockers, mismatched official-deadline claim, late original-source claim and missing original model-consumption/atomic candidate receiver evidence.

Even when **all three claimed source digests** are populated with six exhibition boats, 120 distinct odds and before-cutoff timestamps, `dispatch_authorized=false`, `formal=false`, `independent_first_candidate_receipt_verified=false` and `production_promotion_allowed=false`. A claimed source SHA256 is **not** an independently rehashed original; those claims can be used to *veto* or flag review, not authorize model computation.

A counterfactual source event that occurs **after the original forecast generation** is explicitly labelled `existing_forecast_generated_before_claimed_official_sources`. Do not reuse the early original forecast merely because another collector later obtained valid official data. That would require **new source-consuming candidate computation under a separately approved, predeclared policy**, not relabeling the old bytes.

## Actual live-source observation (from pinned source originals, not newly sampled races)

[CI #42787038161](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42787038161), commit `961040af654d601eae66ae646f8b358690e477a9`, ran the **actual** 150-original Git byte census and the per-race event-handoff veto with **no external claim input** (because no authenticated same-race #1694 packets were supplied). Its log reported:

| Original-source/recipient condition | Count |
| --- | ---: |
| Immutable main forecast original race IDs | 150 |
| Forecasts with absent `beforeinfo` field data | 150 |
| Official-source handoff claims **supplied to this tool** | **0** |
| Official-source handoff claim missing in tool input | **150** |
| File-declared T−12 already elapsed at 16:33 JST | 125 |
| File-declared T−12 still future at 16:33 JST | 25 |
| Independent official original packets authenticated **by this tool** | **0** |
| Independent first candidate receipts authenticated | **0** |
| Dispatch authorized | **0** |
| Formal pilot / untouched confirmation | **0/300 + 0/300** |

**Do not infer that actual official archives are empty** from 0 handoff input. The independently audited #1694 source artifacts and unrelated collectors are separate evidence stores; source-handoff evidence must be fetched, matched and authenticated by its owner before inclusion.

## Offline negative controls and CI integration

- `research/test_hole_pair_official_event_veto_audit.py`: **15** new synthetic negative/positive cases, including all-three-complete-looking but unverified claims (still veto), official original missing 1/3, exhibition 5/6, trifecta odds 119/120, same-race forecast predating official source, claimed deadline mismatch, official source after declared T−12, wrong-race / orphan source, forged formal flags, malformed digests, invalid UTC/JST, invalid GitHub artifact ID and empty source universe.
- CI uses only the research Draft's existing PR event and read-only checkout: the new unit tests and per-race veto run **after** the real original-150 Git blob audit, save `research_20261110_official_event_handoff_veto_nonformal.json`, and upload it in the existing `hole-pair-actual-nov10-main-source-audit-nonformal` artifact.
- Initial CI revealed a **test-only** empty-Git-tree input issue (test fixture used a newline where `git ls-tree` has empty bytes); fixed without relaxing the original-source parser. Subsequent [CI #42787038161](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42787038161) passed the **15/15** tests and actual source-handoff veto step.

## Required actual handoff before considering any live integration

1. #1694 (official T−12 owner) must independently verify and supply actual **same-race, original raw bytes** for official racelist, six beforeinfo/exhibition boats and all 120 unique trifecta odds; official original archive and first server publication timing must be joined **for that exact race** against the true cutoff, not a copied deadline.
2. The frozen hole-pair forecast must be generated **after consuming** the audited original sources, with result-blind code pins and no post-hoc selector re-ranking; the current 150 early forecasts cannot be retroactively upgraded.
3. The independently managed candidate receiver must store an atomic **first insert per race** of the exact candidate bytes with authenticated first time, independently controlled signing key, append-only evidence and conflict/duplicate quarantine. The existing unsigned D1 simulation and caller-supplied signing-key verifier do not meet this requirement.
4. Only after external first receipts, complete official day/race schedule reconciliation, and predeclared prospective cohort can accuracy be scored.

**Decision: HOLD.** This audit is an **additional preflight veto**; there is no real event-driven scheduler, real source input handoff, manual dispatch, or signed receiver acceptance. Preserve Draft #1685 and #1702, do not merge main automatically, and do not count any of the 150 early forecasts as eligible hole-pair study observations.
