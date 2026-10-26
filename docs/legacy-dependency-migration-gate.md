# CLEAN legacy data dependency migration gate

Baseline main: `12db90df4fb82c364a70bfb63365ccccee1d7e0b` (2026-10-27 JST).

## Verified dependencies

| Consumer | Upstream | Required preservation |
| --- | --- | --- |
| `index.html` `loadHeldVenues` | old `data/today.json` | Daily venue/race scope, deadline and stale-data behavior |
| `index.html` `loadRaceData` | old `data/races/<key>.json` | Exact race key, phase, source audit, exhibition lanes |
| `index.html` `verifyPredictionOriginal` | old `data/site_prediction_snapshots/<key>.json` plus GitHub commits and first blob | Original-first-add and cutoff provenance, byte identity and scoring safety |
| `index.html` `loadResult` | old `data/site_results/<key>.json` | Confirmed result identity; never backfill pre-result prediction |
| `fresh_formal_source_preflight.py` | old `data/formal_status.json` | Formal readiness and fail-closed guards |

These are **read-only external inputs**. They are not proof of CLEAN being independently provisioned. The CLEAN main tree has no `data/today.json` as of the baseline SHA.

## Current consumers

- `server.py`: standalone live odds HTTP handler and a separate research/predictions feed path. It does not provide the above static `data/*` producers.
- `research_model.py` and `collect_research_daily.py`: research-only daily CSV consumer and repository research snapshot persistence; not replacements for formal saved predictions.
- `fresh_*.py`: candidate intake, receipts and formal status checks; cannot be declared redundant while prospective evidence collection exists.
- GitHub Pages and Render: distinct serving paths; deploy configuration and production routing must be verified separately.

## Safe replacement gates (all required before switching URLs)

1. Produce `today.json`, `races/<key>.json`, `site_results/<key>.json` within CLEAN from independently identified official sources. Validate date, venue and race identity, completeness, publication windows, upstream status, and source provenance.
2. Produce prediction snapshot feeds under an explicitly versioned CLEAN schema with original creation proof. **Do not clone an old JSON snapshot and claim its new repository first-add as proof of pre-cutoff prediction.**
3. Preserve original Git commit provenance via an explicit independently verifiable cross-repository origin reference, or only score new prospective predictions frozen in CLEAN before cutoff.
4. Replace formal status dependence only with authoritative and auditable independently verified readiness; reject unknown or missing metadata.
5. Test race/date switching, stale in-flight response isolation, unavailable upstream behavior, Top3/5/10, official exhibitions and six-lane integrity, and mobile real-browser flows.
6. Deploy to an isolated preview first, prove byte/content parity and actual upstream supply, then review concurrent PRs before altering production routing.
7. Preserve research snapshots, formal evidence and workflows until their consumers and migration alternatives are verified.

## Guard and known limitations

`test_legacy_dependency_guard.py` intentionally pins the two page base URLs and one formal status URL. No automated migration or production deletion is authorized by this document.

Do not modify or delete the old `ikst2512-eng/boat-edge` repository. No assertion of successful live producer migration or mobile regression is made here.
