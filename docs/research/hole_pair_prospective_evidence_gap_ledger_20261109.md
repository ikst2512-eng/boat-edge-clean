# Hole-pair ⑤: candidate-level evidence-gap ledger (2026-11-09 JST)

**Draft PR #1685 only. No main merge, gateway dispatch, new receiver, network call, production predictor, collector, Render, Cloudflare or UI edits. Formal pilot 0/300; untouched confirmation 0/300.**

## Purpose

This is a small, **result-blind gap classification and #1694 official-source audit handoff**, not another source collector or a way to certify first external acceptance. The existing #1685 candidate D1 validator already audits whether a **claimed** local candidate JSON and **self-reported** D1 SQLite acceptance clock are mutually consistent. The new `research/hole_pair_prospective_evidence_gap_ledger.py` lets reviewers apply that existing validator to **all frozen and excluded race IDs** in one already-captured immutable-main manifest and receive per-race blocker codes.

It deliberately **does not authenticate** provider-origin responses, does not fetch GitHub/Cloudflare/official sources, does not open winners, and cannot turn a source-audit report pointer into official six-boat/120-odds proof. Official three-original replay and source-origin verification remain with #1694 / owner①; source data or signed independent witness must be validated externally before a separate review can authorize prospective study admission.

## Inputs

1. `research_candidate_freeze.json`: the *original*, nonformal `HOLE_PAIR_FUTURE_ACTIONS_BATCH_V1` snapshot produced by an explicitly authorized manual research run, **if** one exists. Exact race IDs, nonformal flags, exclusion mapping, candidate schema and frozen Top5 protections are rechecked through the existing `reconcile` / `audit_one` validators.
2. **Optional** JSON map of race code to D1 `HOLE_PAIR_D1_FIRST_ACCEPTANCE_V1` response. Must match candidate record SHA256, local finish, declared T−12 clock, and D1 contract. A matching receipt is labelled **`self_reported_d1_timestamp_consistent_not_independent_proof`**. A repeated receipt never increases the denominator.
3. **Optional** JSON map of race code to a *claimed report pointer* with **exactly** `race_code`, `upstream_report_sha256_claim` (64 lowercase hex characters) and `upstream_report_locator_claim` (bounded identifier string). This is solely a matching-race handoff to the independently owned #1694 source auditor; these fields are **not authenticated evidence**, and the tool never treats them as proof of official completeness. Different race ID or arbitrary `formal`/verified flags are rejected.

All data remain untrusted even if a caller adds a plausible SHA or a supposedly authoritative source locator.

## Example command (only after a real nonformal manifest exists)

```bash
python research/hole_pair_prospective_evidence_gap_ledger.py \
  --manifest /path/to/research_candidate_freeze.json \
  --d1-receipts /path/to/d1_self_reported_receipts.json \
  --source-report-pointers /path/to/unverified_source_report_refs.json \
  > prospective_evidence_gaps_nonformal.json
```

Both optional inputs may be omitted. The script reads supplied local JSON files only and prints a report; it **does not rewrite the manifest or calculate predictions**. The report shows one row per original snapshot race ID: frozen candidate versus explicit exclusion; candidate SHA256, original source SHA claims, self-reported D1 status, source-audit pointer presence and exact missing-evidence reasons. For every candidate, those include independent first acceptance, official deadline, same-race official racelist, six-lane exhibition, 120 distinct odds, original input consumption, after-source/before-cutoff generation, cross-run first write, whole-day schedule and independent result. Excluded IDs stay visible but do not become candidates.

Crucially, **every** output has `formal=false`, `prospective_pilot_formally_eligible=0`, `prospective_confirmation_formally_eligible=0`, `accuracy_denominator_authorized=false`, and `production_promotion_allowed=false`. The tool itself is not capable of an "all gates satisfied" outcome; that would require separate independently authenticated receipts and source audits plus explicit manual review.

## Test and CI evidence

- Added `research/hole_pair_prospective_evidence_gap_ledger.py` and `research/test_hole_pair_prospective_evidence_gap_ledger.py`.
- Updated **PR-only** `.github/workflows/hole-future-pair-precommit.yml` to include them in paths and run the tests. No capture or scheduler job was added.
- [Actions #42618146159](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42618146159), tested head `914eb9406bc83b11330c1ed2041629a9e27ae383`: **success**, **15/15 new synthetic tests** passing, as well as existing read-only research gates. The real manual candidate-freeze step and candidate upload were **skipped** on the PR event. Existing readiness artifact does not certify a single candidate.

## Real external blockers that this must not obscure

The independent [Nov 9 same-race audit #1694](https://github.com/ikst2512-eng/boat-edge-clean/pull/1694) documented two real official **beforeinfo + 120-odds pair** archives whose source ZIPs were posted before T−12, but had no same-race archived racelist original; existing forecasts were created before the official originals, and first forecast remote acceptance was not proven. That evidence belongs to #1694 and is **not a new eligible hole-pair record**. None of the historical Nov5–8 106/102 shadow results may enter the prospective cohorts.

**Decision remains HOLD:** #1702 preferred for a *single* future manually reviewed research gateway over competing #1701, but no merge/dispatch. Un-deployed D1 clock claims and Git readbacks are not signed independent first-receipt proofs. Preserve the locked #1685 two-policy selector and all historical original candidates; no post-outcome tuning. Formal accuracy remains undefined; 0/300 + 0/300 eligible.
