# BOAT EDGE CLEAN: position-sensitive four-mode candidate (2026-11-08 JST)

Status: **Draft research / NOT deployed / NOT certified / no betting recommendation**.

## User concern, measured problem

The archived four-mode V2 `research_model.probabilities` applies the six national win rates to the FIRST-boat component. For any fixed first boat, all second/third probabilities are proportional to the same frozen 1,000-case ticket-count prior. Consequently `1-2-4` and `1-2-3` have virtually invariant relative order across races even when boats 3 and 4 have sharply different win rates.

Independent existing Draft [#1693](https://github.com/ikst2512-eng/boat-edge-clean/pull/1693) already audited **116** Nov-08 frozen V2 inputs and identified **109/116** top picks `1-2-4`; follow its stronger full-cohort provenance and first-head exposure safeguards. The current change is a NEW, **isolated conditional-second/third ranking candidate**, not a duplicate Top1 protocol or ledger.

## What the candidate actually does

- Read only a six-boat national win-rate vector. Recompute the unchanged frozen V2 research 120-ticket baseline.
- For a tuple (first h, second s, third t) multiply the baseline probability by:
  `exp(0.50 * (rate[s] - mean(rates except h)) + 0.25 * (rate[t] - mean(rates except h,s)))`.
- Normalize **separately within each first-boat h**, leaving all six baseline first-boat marginal probabilities unchanged. This makes the relative ranks of 2nd/3rd reflect the race-specific six-boat skill inputs. It does **not** fix first-boat (escape/wall) bias or independently establish better prediction.
- Apply the existing `rank_modes` selector. Exactly preserve the current candidate ticket budgets: narrow 5, hit 10, balance 16, hole 22. These are existing exploratory budgets, not proven best sizes.
- Coefficients 0.50/0.25 are **hypotheses**, frozen BEFORE outcome comparison, not statistically fitted or validated. No odds/returns/results/exhibition/ST/wind/motor/course are used. Missing mandatory features are not invented.

## Early input-only replay (not hit-rate evidence)

With the fixed candidate and 12 selected Nov-08 saved six-rate vectors, the **top-1 combination changed in 9/12**, while top-5 membership changed in **11/12**. These are **changes**, not improvements in accuracy, win-head coverage or ROI. Example:
- `202611080102`: baseline top1 `1-2-4`, candidate top1 `1-2-3`.
- `202611080302`: baseline top1 `1-2-4`, candidate top1 `1-3-5`.
- `202611080303`: baseline top1 `2-1-3`, candidate top1 `1-2-3` — potentially worse; do NOT select using after-result knowledge.

A repeatable full-day **input-only** diagnostic is provided:
`python four_mode_position_sensitive_shadow.py --day 20261108`.
This checks every present original saved V2 against the recomputed baseline and compares rank diversity without reading any finish or payout. The output counts cannot prove skill.

## Promotion gate / division of work

1. **Do not change main, Render/UI, live selection, T-12 pipeline or saved historical predictions.** Files in this Draft are research-only and have no production import path.
2. In the research coordinator **#1693**, retain the existing prospective 300+300 Top1 and all-mode paired validation protocols. A new candidate must be predeclared separately (exact selector SHA, coefficients, data-provenance/first-remote-receipt) BEFORE the future race. Do not slip this candidate into an already preregistered identity.
3. After a legitimate predeadline independent candidate freeze, score same-race old vs new Top1/Top3/Top5/Top10, wins/losses, venue/first-head strata, calibration and ROI with independent results, and include risk of deterioration. NO Nov-05–08 development comparisons in the prospective holdout.
4. Use the 24-venue wind/actual-course research in Draft **[#1692](https://github.com/ikst2512-eng/boat-edge-clean/pull/1692)** only when trustworthy race-specific before-deadline receipts are available. Never infer missing weather/exhibition/wall inputs.
5. UI/Render audit remains **[#1679](https://github.com/ikst2512-eng/boat-edge-clean/pull/1679)**. This PR deliberately avoids UI and server routing so it cannot compromise the already-unresolved production HTTP issue.

### Cross-chat handoff

**Shared reference: this Draft PR** (URL linked from PR itself). For any other BOAT EDGE CLEAN ChatGPT conversation:

> Main is unchanged. Inspect the position-sensitive four-mode shadow Draft and its tests. Current V2 fixes second/third ordering to one historical prior; new candidate independently tilts second/third probabilities using six national rates and preserves each first-boat mass. Its 12-race input-only replay changes Top1 in 9/12 and Top5 membership in 11/12, NOT verified accuracy. Coordinate with #1693 (forward validation), #1692 (venue/wind evidence), #1679 (UI/Render). Never overwrite old predictions or auto-merge. Do not adopt until independent future paired evidence proves gain.

**No automatic synchronization to separate ChatGPT threads exists**; the GitHub Draft is the canonical shared handoff.

## Exact-head GitHub Actions verification (2026-11-08 15:52 JST)

[Read-only CI #42456489975](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42456489975) **SUCCESS**, at Draft head `c20ce06e600cd11b8c93c42bfe4bc8129765f2f2`. Eight unit and negative tests passed. Input-only replay compared **116/116** original saved V2 files, **0 excluded**, verified exact recomputation of their original tickets and NEVER loaded confirmed results. No publication, model or runtime deployment.

| Saved Nov-08 cohort metric | Existing V2 | Position-sensitive shadow |
| --- | ---: | ---: |
| Hit/narrow/balance most common Top1 (`1-2-4`) | 109/116 | 42/116 |
| Hit/narrow/balance distinct Top1 combinations | 3 | 11 |
| Hit/narrow distinct Top5 ordered lists | 13 | 95 |
| Balance distinct Top5 ordered lists | 19 | 100 |
| Hole distinct Top1 combinations | 15 | 40 |
| Hit/narrow Top1 changed vs baseline | — | 76/116 |
| Hit/narrow Top5 membership changed vs baseline | — | 103/116 |
| Balance Top5 membership changed vs baseline | — | 106/116 |
| Hole Top1 changed vs baseline | — | 107/116 |

Although 6/116 hit/narrow/balance Top1 **first-boat numbers** changed, the candidate preserves the marginal first-boat probability exactly; this is reallocation among 2nd/3rd combinations, NOT evidence of improved first-place forecasts. **No historical outcome scoring or forward holdout was performed.** Archived original and live predictions are unchanged.
