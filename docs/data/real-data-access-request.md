# Source access and rights request prepared for the user

Status: UNSENT. No source is approved for the new sprint. No password, API secret,
broker connection, payment, subscription or terms acceptance is requested.

## Route 1: strongest coverage candidate

Name: TejHQ Indian Markets. Publisher: TejHQ.
[Dataset and publisher discussion route](https://huggingface.co/datasets/tejhq/indian-markets/discussions).
License evidence: dataset metadata MIT, body MIT pipeline / exchange-published data.
Current project decision: INSUFFICIENT_RIGHTS_EVIDENCE, not APPROVED_RESEARCH.

The user can ask the publisher for a public clarification or applicable grant:

> AlphaLens proposes local noncommercial research on NSE cash common equities,
> including dataset retention/normalization, technical features, supervised model
> training, chronological walk-forward evaluation and hypothetical historical
> backtesting. No raw-data redistribution, product deployment or real orders are
> proposed. Please clarify whether the dataset MIT declaration applies to the raw
> NSE price/action files and identify the applicable source authorization addressing
> NSE's reproduction, research-access and virtual-trading/simulation conditions.
> Please also identify acquisition provenance, deleted-row counts, original decimal
> precision, historical publication/availability evidence, corporate-action
> announcement dates and departed-security completeness. We need a zero-cost
> permission covering 2014 (preferably earlier) through the latest 2026 session.

This draft is newly authored, not a quote or a message sent to the publisher.
An open dataset grant plus repository uploader representations can support research
with residual risk under D36; the request addresses identified specific conditions,
not independent verification of every upstream right.

## Route 2: official NSE academic-research access

[NSE research initiatives](https://www.nseindia.com/static/research/research-initiatives)
links the [Data Seeking Request Form](https://nsearchives.nseindia.com/web/sites/default/files/inline-files/Data%20Seeking%20Request%20Form-20250319.pdf).
If the user actually meets the stated institution/research-organization eligibility,
they can complete it and submit it themselves to the address published on that
page, `nseri@nse.co.in`. Do not invent an institutional affiliation. No contact
has been made by AlphaLens. The public form is approximately 82 KB.

Suggested non-personal form content:

- Project: AlphaLens - chronological NSE cash-equity prediction research.
- Objective: compare predefined price/volume classifiers/regressors against naive
  baselines using immutable provenance, point-in-time universes and leakage-safe
  walk-forward evaluation; report weak/negative results without investment claims.
- Data: daily reports and historical security/reference/corporate-action/calendar
  records; NSE cash common-equity OHLCV, stable identifiers, dated symbols/types,
  departed listings and price-index benchmark observations.
- Period: 01/01/2014 through the latest available 2026 session; preserve earlier
  legitimate warm-up observations if supplied.
- Justification: assess predictive/ranking stability across multiple market periods,
  with explicit exclusions, transaction-cost assumptions and no real execution.
- Rights to request explicitly: local retention, normalization, feature/label
  computation, model training, offline hypothetical P10 backtesting and internal
  derived research reports. Request written confirmation of zero cost, applicable
  aggregate-volume limits, confidentiality/reporting conditions and whether the
  hypothetical research backtest is permitted despite the general website condition.

Free delivery is **not guaranteed**. The published policy separates freely available
research reports from voluminous chargeable archives, with possible applicable
arrangements. If only a paid license is offered, do not purchase it or silently
change the project's zero-paid rule. A later user scope amendment would be required.

## Files and integrity strategy after rights approval

Only after a source passes the documented gate:

1. Put original downloaded files and permission/attribution evidence in
   `C:\Users\Dell\AlphaLens\data\incoming\`. Keep the archive intact; never
   replace the only original with a cleaned CSV.
2. For TejHQ, if approved, select `nse/year=2010/nse_2010.parquet` through
   `nse/year=2026/nse_2026.parquet` at revision
   `14d81bbaef8c0f8dc673fb3e3573f9e1f32bed98`: 17 price files, expected combined
   metadata size 192,163,454 bytes (about 183.3 MiB). Do not download BSE, metrics,
   back-adjusted prices or publisher universe to substitute for P4/P6. Optional
   approved NSE action-year files and symbol-history supplement have not been sized.
   No NIFTY benchmark is established by this package.
3. Compute each original-file SHA256, record bytes/date/publisher/version/reference
   and compare with the pinned LFS digest and size in `source-audit.json`. These are
   publisher expected digests, not already verified downloads. A changed snapshot
   requires a new audit/identity. If delivery uses an archive, hash both intact
   archive and individual members and retain the member mapping.
4. Use P2 LocalFileSource and immutable raw storage before source-specific parsing.
   Source identity is a nonsecret dataset reference, not a credential-bearing URL.
5. Profile source files without silently removing anomalies; independently report
   asset types, missing clocks, duplicates, gaps, departed coverage and actions.
   A calendar-date column is not historical publication evidence. Do not assign
   guessed EOD publication times to make P6/P7 eligibility pass.

PowerShell integrity command, after files and approval exist:

```powershell
Get-ChildItem -LiteralPath 'C:\Users\Dell\AlphaLens\data\incoming' -File |
    Get-FileHash -Algorithm SHA256
```

If the selected approved delivery needs browser login/manual terms acceptance,
the user must complete those steps themselves. AlphaLens must stop until original
files and permission evidence exist; no passwords/API secrets should be shared.
At present the blocker is rights/scope evidence, not a login failure.
