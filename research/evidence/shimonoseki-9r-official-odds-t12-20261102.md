# Shimonoseki 9R: official 3T odds observed before T−12 (2026-11-02)

**Research observation only. Does not certify formal prediction readiness.**

- Race: `202611021909` (Shimonoseki 9R), official beforeinfo deadline `21:25 JST`; T−12 cutoff `21:13 JST`.
- Original official beforeinfo JSON received `20:43:31.219899 JST` with SHA256 `c4e3ee53a53510749ea116c52e4fd8ca66f68ce0935ac2cc25c9f9b5e85992a7`.
- Original official 3T odds HTML received `20:43:39.452298 JST`, **29 minutes 20.548 seconds before T−12**.
- Original odds HTML: 45,973 bytes, SHA256 `87e3809a52c38dcd726c6fd238f23cd986f9c2efe47c85caa663337d2b329ec0`. Archived source independently re-read and SHA256/byte size compared with the original manifest (both match).
- Existing parser found 120 distinct valid trifecta combinations; the existing `inspect_official_odds_receipt` gate returned `complete_odds_observed_before_t12=true`.
- Evidence: [GitHub Actions run 41438998300](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/41438998300), artifact `13138320884`. Temporary PR #992 closed without merging.
- At the same time, official beforeinfo exhibition times were **0/6** and start exhibition **0**, so this is **not** an all-inputs-complete or forecast-eligible case.
- Original collector leaves `source_immutability_verified=false` by design. Independent archive file SHA256 match is recorded here and does not override that collector's default provenance flag.

No formal forecast/ROI/accuracy claim; no four-mode changes.
