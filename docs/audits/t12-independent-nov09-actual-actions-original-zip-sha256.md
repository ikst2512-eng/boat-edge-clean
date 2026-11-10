# 2026-11-09 — actual original GitHub Actions ZIP digest independently verified

**Scope:** isolated, read-only source-provenance evidence for the fixed November 9 two-source cohort. Draft PR #1694 only; no prospective accuracy claim or source acquisition added. Auditor's **GitHub connector** supplied the actual downloaded original ZIP (not a repacked archive) as an ephemeral file for independent SHA256 and full ZIP CRC checks.

- Repository: `ikst2512-eng/boat-edge-clean`.
- GitHub Actions collector run: [#42567310743](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42567310743), `event=schedule`.
- Original artifact: [#13652131213](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42567310743/artifacts/13652131213), `independent-late-preview-42567310743`, current GitHub API `expired=false`.
- **Actual original ZIP**: **28,063 bytes**, independently computed SHA256 **`99f02ff306307dd945f27c225e18ff8341be2832232b7dd0f2751e1d8935f451`** equals the exact current GitHub metadata `digest=sha256:...`.
- ZIP member count: **16**; Python `zipfile.testzip()` processed all compressed members and returned **None (all CRC valid)**.
- Exactly **two different race IDs** and exactly **four original source content files** plus four manifests in that ZIP; **no original official racelist HTML filename** in any of the 16 members. Four publish-lock files and four supporting reports are not new source originals.

| Race | Source | Independently hashed original bytes | SHA256 matches its manifest |
|---|---|---:|---|
| `202611091110` びわこ10R | beforeinfo JSON | 4,574 | `20292be74ef310690a3e5678ff730d657c5c2636e1c8638f42942132d39ff25d` — yes |
| `202611091110` びわこ10R | official 3T odds HTML | 46,462 | `c568ad65600f89f6536476e49729f2f3acd58fba42365159df3bea7de3f59098` — yes |
| `202611091710` 宮島10R | beforeinfo JSON | 4,365 | `792c04684494c5aee603acafd9ded3256a927cad5bea8364ca2a19046c4fd036` — yes |
| `202611091710` 宮島10R | official 3T odds HTML | 45,856 | `07c39b89b51ad0b1bff7f48cbb3881a507fc14cc0aa1b3babb72773a45087fa5` — yes |

Each of the four raw original file lengths also matches the exact `bytes` property in its own manifest. Recorded collector receipt clocks are **self-reported within artifact**, not independent GitHub receipt clocks:
- びわこ10R beforeinfo 14:26:50.194266 JST, odds 14:26:59.498535 JST; recorded T−12 14:30.
- 宮島10R beforeinfo 14:26:32.711772 JST, odds 14:26:41.921482 JST; recorded T−12 14:28.

**What this new verification closes:** the previous audit checked re-packed extracted bytes and separately matched GitHub's stored ZIP digest metadata, but reported `github_original_zip_digest_locally_rehashed_by_ci=false` because CI did not directly download the original byte-for-byte ZIP. The actual original ZIP is now independently rehashed **outside CI**. We intentionally do **NOT** alter the old CI replay's `false` field (truthful CI-specific statement). An additional optional safe original-byte verifier was implemented in the same existing `audit_t12_extracted_artifact_replay.py` (not a duplicate full T−12 audit) with fail-closed metadata, SHA, CRC, path traversal and provenance safeguards; CI regression tests cover its behavior. The direct original archive is not committed to git or uploaded elsewhere.

**What this does NOT prove:** that the source collector's own request/receipt clocks were independently witnessed; presence of the **third official racelist original**; actual model consumption; a genuinely generated forecast following official sources; independent **first forecast Git remote acceptance**; or final official race entry. GitHub server source-ZIP archive publication remains different from first forecast acceptance. **Fully complete same-race official triads 0, formal certified forecasts 0, formal accuracy denominator undefined**.

**Boundary:** No collector/Cron change (#1699 owns scheduling), no #1709 cleanup merge, no Render/UI/forecast/main modification; #1694 stays Draft and no automatic merge.
