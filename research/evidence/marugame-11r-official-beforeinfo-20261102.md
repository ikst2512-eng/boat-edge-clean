# Verified official beforeinfo T−12 source observation — 2026-11-02

Research-only evidence, **not** a production forecast-use certification.

- Race: 2026-11-02 Marugame 11R, `202611021511`
- Official endpoint: `https://www.boatrace.jp/owsp/sp/spdata?type=beforeinfo&hd=20261102&jcd=15&rno=11`
- GitHub Actions source capture: [run 41432104749](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/41432104749), artifact `13134398614`, experimental PR #957 (closed without merge)
- Original file: `source/observations/run41432104749/20261102/202611021511/beforeinfo.json`
- Original response SHA-256: `345c111ad825d809668833c2960fef4ec69d72f5050c83ca80ffee3f0238acdb`
- Original bytes: `4553`
- Request started JST: `2026-11-02T19:51:25.485829+09:00`
- Source fully received JST: `2026-11-02T19:51:35.789185+09:00`
- Original official deadline display: `20:06`, corresponding to T−12 at `19:54:00 JST`.

## Reinspection findings

Original archive was extracted and the raw response SHA-256, size, race identity, official deadline/time arithmetic, chronological receipt, six distinct boat identities, six positive finite exhibition times, six finite tilt readings, and six valid start-exhibition rows (distinct boats 1–6, courses 1–6 and numeric/F/L ST string formats) were checked again.

**Pass**: complete official beforeinfo fields observed before the T−12 cutoff, by 2 minutes 24.211 seconds at receipt time.

**Not established**: all required prediction inputs available before T−12, complete provenance for BOATERS/odds, any full formal forecast eligibility, prediction model improvements or production website changes. `t12_eligible=false` and `forecast_usable=false` remain enforced. In particular, a six-row start exhibition alone is not enough.

This report records a manually rechecked archived observation. GitHub Actions cron invocation success/failure at 19:48/19:52 is **not independently verified** by this artifact; do not conflate the experiment's capture with those scheduled runs.
