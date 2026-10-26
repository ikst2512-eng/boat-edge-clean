# Formal Fresh 120-way connection contract (LOCKED)

This document is a consumer-side specification, **not** an approval, a validated model, or a Fresh100 result.

## Current state

- Formal V1.21.20 executable source and immutable weight/config artifact: **not located**.
- Recorded parent SHA-256: `11e6d19c1f2bbcaac98adbf82cf0043c9752c7f79f55728d619b1de9c1a747db` (an identifier alone does not authenticate an artifact).
- An untrusted `predictions.json` entry, including `validated: true`, must never activate formal output.
- `research_model.py` output must remain `status: research`, `validated: false`; never use as a formal input or fallback.
- Results, payouts, scoring, unlock, and retrospective regeneration must stay disabled.

## Producer-to-consumer evidence contract (not yet implemented)

For every prospective race, the isolated formal producer must emit:

1. Race identity (date, venue code, race number), **official** deadline with timezone and source URL/content digest.
2. Full 120 unique legal ordered trifectas with finite numeric probabilities in [0, 1], normalized to 1 within a documented tolerance; no Top10-only feed.
3. Approved model identity and exact executable/config/weights digests, verified against a separately controlled allowlist; immutable model Git SHA (not merely a self-declared version).
4. Complete CORE7 input provenance: source names, source acquisition timestamps, bytes/content SHA-256, actual entry / exhibition completeness, missing-field policy and race binding. Eligibility is false when mandatory inputs are absent.
5. Generation timestamp, predeadline freeze cutoff, canonical artifact digest and signed or independently verifiable Git/object-store immutable first-write receipt. Audit the **first appearance** and download-and-hash the bytes independently. Repository commit time or server reception time alone is insufficient.
6. Strict monotonic lifecycle: `COLLECTED -> FROZEN -> VERIFIED -> DISPLAY_ELIGIBLE`; any failed check is `LOCKED`. Replays, updates, late data, missing receipts, or deadline uncertainty never auto-unlock.
7. Separate `formal` and `research` API/UI channels. Only a trusted verifier (not the feed itself) may set `validated: true`.

## Acceptance tests before enabling formal display

- No source, truncated list, duplicate combo, NaN, negative probability, wrong sum, wrong race, wrong model or stale/late timestamp -> unavailable.
- Forged `validated: true`, forged Git SHA, overwritten artifacts or self-supplied verification receipt -> unavailable.
- Research-only forecasts remain labelled research, are never counted toward formal 100R, and never trigger result access.
- One *future* race: independently verified official deadline, frozen 120 distribution and immutable receipt are reproducible from downloaded bytes.
- Formal 100R requires independently approved first-100 cohort with per-race CORE7 and all pre-result receipts; do not infer it from 100 site records.

**Never enable scoring, results access or unlock as part of this integration work.**

## Dependency and merge order

1. Recover authentic V1.21.20 executable/model artifact; independently hash it.
2. Build isolated pre-result producer + read-only independent verifier with synthetic negative tests.
3. Capture one real race before cutoff; independently verify artifact bytes.
4. Wire read-only verified output to CLEAN API/UI, retaining fail-closed status.
5. Formal 100R acceptance requires a separate explicit review; no automatic promotion.
