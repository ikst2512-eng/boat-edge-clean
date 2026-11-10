# 2026-11-08 ~20:30 JST — Three-original chronology/readiness independent audit

Status: **research-only**, **formal certified 0**, formal accuracy denominator **undefined**. This report extends [11/8 18:01 original-source audit](t12-independent-nov08-1800-recheck.md) and [~20:14 transport/provenance update](t12-independent-nov08-2015-transport-and-provenance.md). No collector, model, Render, main or scheduler changes are authorized from this audit.

## The new audit-only gate

A future successful *original three-source archive* can now be inspected with:

```sh
python -m scripts.audit_t12_three_original_frozen \
  --racelist-dir evidence/.../official_racelist \
  --beforeinfo-dir evidence/.../official_beforeinfo \
  --odds-dir evidence/.../official_odds \
  --frozen-forecast path/to/immutable-frozen.json \
  --output reports/three_source_frozen_replay.json
```

**The directories are placeholders**, not evidence the Nov 8 three-source archive exists. This CLI first reruns the existing official original-byte/URL/hash/registration audits. It requires the 12 independently replayed official component checks and literal true evidence, all three original receive timestamps before official T−12, and a *strictly later* frozen forecast not after T−12. For diagnostic model linkage, the forecast must explicitly declare `input_source_kind=official_three_originals` and carry all three matching `official_original_sha256` values. A SHA map recorded by a model **does not independently prove it consumed the bytes**; that gate is explicitly *unverified*. Independent initial GitHub remote receipt and final race entry are also unverified by this source-chronology audit. Even on fully aligned synthetic fixtures, `formal=false`, `t12_eligible=false`, `forecast_usable=false`, and `accuracy_scoring_allowed=false` always.

Where the Nov 8 official two-source archive has no original racelist, the raw three-source CLI **cannot pass** and must not be bypassed with a fabricated card. It is deliberately not an automatic promotion path.

## Newly observed live evidence

- [#42475750571 at 20:26 JST](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42475750571): **entry-course T−2 study**, separate research workflow, failed. The `COURSE_LATE_EVIDENCE` job log reports `status=t2_missing_expected_t12_baselines`, `missing_baseline_race_codes=["202611080112"]` (**桐生12R**). Its 103 research snapshot files and 1 current eligible candidate are *not* official boatrace.jp three-original receipts. Hand off baseline persistence to the entry-course research owner; do not modify the T−2 collector from this PR.
- Official two-source [#42450048245 at 14:15 JST](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42450048245) remains the only observed scheduled activation for `research-live-preview-evidence.yml` in the bounded Nov 8 schedule inventory. [Nov 8 schedule list](https://github.com/ikst2512-eng/boat-edge-clean/actions?query=event%3Aschedule) at ~20:28 JST contained **42 total workflow runs** created on Nov 8 UTC, but only **one** matching the official-pair collector path. Nominal slots from 09:00 to 20:25 JST inclusive: **138**, so count comparison **1/138 ≈ 0.72%**. This is NOT 137 proven HTTP errors, not exact slot attribution, and not conclusive GitHub scheduler root cause.
- The [19:37 Render API odds probe #42472229918](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42472229918) had 6/6 TimeoutError attempts across 3 races and 0 valid HTTP 200; this does **not** prove official boatrace.jp request failure. The separate 20:14 [CSV six-lane probe #42474841935](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42474841935) succeeded for 住之江11R `202611081211` but was ~10m17s after its **CSV-derived** T−12; it does **not** supply the official archived racelist/beforeinfo/120-way odds.

## Highest impact path to a genuine first positive certificate

1. **Owner ①:** Demonstrate reliable, actual same-race collection of official racelist HTML, official beforeinfo JSON with six boats and ST/exhibition, and official odds3t HTML with 120 unique valid tickets, all before *official* T−12. Fix invocation gap first and report actual source HTTP statuses; green job ≠ raw original evidence.
2. **Owner ①:** Produce a **new** frozen prediction strictly after the latest raw receipt (do not rewrite 10:12 or 10:17 forecasts); preserve byte-level source-to-model input provenance independently from self-reported SHA values.
3. **Independent audit:** Re-read raw archives; verify all 12 components, 3 individual hashes, source identity and chronology; then independently attest initial GitHub remote receipt, final entry, and immutable prediction. Do not turn on formal scoring from three-source diagnostics alone.

**Do not merge** Draft #1694 into main automatically or touch collectors. Audit checks and synthetic tests are not a substitute for a live prospective official triple.
