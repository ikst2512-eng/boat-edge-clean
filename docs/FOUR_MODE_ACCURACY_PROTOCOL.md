# Current four-mode contract — verification against main

This document records the existing implementation. It does not authorize changing
prediction strategy, ranking, stake allocation, mode thresholds, or UI.

## Canonical display and data
- `index.html` displays **AI予想｜4モード** with labels 本命・バランス・穴・絞り.
- The read-only API `GET /api/four-mode-archive?code=...` is implemented in
  `four_mode_archive_api.py`.
- It reads `four_mode_forecasts/<race_code>.json` with schema
  `CLEAN_FOUR_MODES_PREDEADLINE_V1` and keys `hit`, `balance`,
  `hole`, `narrow`. Tickets contain `combo` and `p`.
- The API explicitly returns `historical_research_only`,
  `production_forecast:false`, `verified_first_git_add:false`,
  and `actual_hit_rate_pct:null`. Do not claim formal measured accuracy.
- `four_mode_performance/verified_races` is a **different**, historical
  simulated-performance data source (`simulated_only:true`). Never combine it
  with current prediction results without matching verified prediction identity
  and evidence.
- `prospective_predictions/` and its Top3/Top5/Top10 metrics are single-list
  legacy research; do not treat any Top-N list as a four-mode output.

## Evaluation gates (no performance claim yet)
- Read and freeze the existing four mode tickets, mode identity, model version
  and decision state before the actual race cutoff; verify independent first
  appearance with trustworthy remote evidence.
- Match each mode on identical race-code and result, using immutable historical
  inputs. Keep skipped/unknown/unverified cases explicitly separated.
- If stakes and payouts have independently verified sources, report separately
  per mode the selected-race count, wins, total stakes, total returns and ROI.
  If no stake is recorded, do not fabricate one or calculate actual ROI.
- Never translate `target_hit_rate_pct` or `estimated_coverage_pct` to
  empirical success rates.
- Preserve the exact current ticket order and mode-specific selection logic.
  **Mode objectives and thresholds are defined by existing implementation,
  not by assumptions in this documentation.**

## Outstanding evidence
The independent historical audit on the separate single-list prospective
candidate system has rejected old timestamps. That result is **not** itself a
four-mode archive audit. A four-mode-specific remote first-add cohort audit is
still needed before reporting formal accuracy.
