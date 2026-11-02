# BOAT EDGE CLEAN — four-mode accuracy protocol

The current primary research modes are **本命 / バランス / 穴 / 絞り**.
Top3, Top5 and Top10 are legacy ranked-ticket diagnostics, **not** the four modes.
Do not equate any Top-N subset with a mode.

| Mode | Objective | Primary reporting |
|---|---|---|
| 本命 | Hit-rate first | trifecta hit rate, eligible races |
| バランス | Hit rate and return | trifecta hit rate, ROI, investment |
| 穴 | Higher payout outcomes | hit rate, ROI, payout distribution |
| 絞り | Only qualified positive-value opportunities | selection rate, selected-race hit rate, ROI, skipped count |

## Canonical implementation verified against main (2026-11-02)
- The existing user-facing prediction panel in `index.html` already displays **AI予想｜4モード** and reads `GET /api/four-mode-archive?code=...`; do not replace it with Top-N.
- The canonical reader is `four_mode_archive_api.py`: `four_mode_forecasts/<race_code>.json`, schema `CLEAN_FOUR_MODES_PREDEADLINE_V1`, with modes `hit`, `balance`, `hole`, `narrow`. Each contains `tickets` entries `{combo,p}`.
- That API expressly returns `historical_research_only`, `production_forecast:false`, `verified_first_git_add:false` and `actual_hit_rate_pct:null`. Do **not** interpret it as validated production four-mode performance.
- The distinct `four_mode_performance/verified_races` records are historical **simulated** performance, not current formal predictions. Keep the existing UI separation.
- The current focused PR's `collect_clean_prospective.py` emits **one** national-beta ranked list, not four per-mode outputs. Its corrected timestamps must not be advertised as a four-mode generation fix.
- The mode names above are existing implementation labels, not permission to change model objectives, allocation, buy/no-buy thresholds or display format. Preserve actual implementation decisions unless separately tested and authorized.

## Cohort and provenance
- Each mode must preserve its **own frozen tickets, selection state, stake, forecast timestamp, source receipts and model version** before race cutoff; never infer these from another mode's Top-N.
- Evaluate all four modes on the same eligible race inventory, while reporting `絞り` selection rate and chosen-race performance separately; skipped races are **not losses**.
- Report numerator and denominator, total invested yen, returned yen, and ROI = returned/invested × 100, separately per mode. Zero-investment ROI is **N/A**, not zero.
- Explicitly distinguish research simulation, local Git first-add evidence, and independently verified remote pre-deadline forecasts. No formal accuracy claims without the latter.
- Invalid provenance, missing result, missing or late mode snapshot, and post-race reconstruction must each remain visible as exclusions; never silently drop them.
- Never rewrite existing prospective archives or relabel their Top-N list as mode outputs.
- Existing Top-N diagnostics remain available only as legacy supplementary research and must not be displayed as four-mode performance.

## Implementation gate
This document sets the reporting contract, **not** a claim that four-mode archives or a validated four-mode evaluator exist. Before replacing an accuracy widget or publishing metrics, connect the actual four-mode forecast output schema, capture each mode independently before the cutoff, and test accounting and provenance. A name-only UI replacement would be misleading.
