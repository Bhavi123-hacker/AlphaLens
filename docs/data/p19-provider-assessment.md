# P19 ongoing daily provider assessment

Assessment date: 2026-10-09. This is an ongoing-source audit, not a revision of
D69 authorization for the exact pinned TejHQ historical archive.

| Candidate | Observations and identity | Timing, revisions and coverage | Permissions and decision |
|---|---|---|---|
| [TejHQ public native Parquet](https://huggingface.co/datasets/tejhq/indian-markets) | NSE yearly OHLCV, symbols, series, names and observed ISINs; separate actions/symbol history | Public metadata reports revision `2e81ae0171ec411e6bff50a302ee6a54fa030459`, modified 2026-10-08T21:15:39Z. Yearly rollups are mutable across revisions. Latest price date was **not measured**, because new prices were not downloaded. Receipt is not historical publication. Historical special-session gaps remain. Raw versus derived/adjusted trees must remain distinct. | Card declares MIT. Prior user authorization pins `14d81bbaef8c0f8dc673fb3e3573f9e1f32bed98`; it does not establish ongoing upstream exchange permission. **SOURCE_CONDITIONALLY_SUPPORTED**, daily activation blocked. No rate-limit bypass, API keys or paid Pro products. |
| [NSE daily reports](https://www.nseindia.com/all-reports) | Official cash-market report resources; full-release series may include non-common instruments | Requires verification of release completeness, session, correction vintage and actual receipt. A public listing does not guarantee publication at a fixed time. | [Current NSE terms](https://www.nseindia.com/static/nse-terms-of-use), clauses 8–9, restrict retention/use and systematic automated collection. **SOURCE_NOT_CLEARED**. No downloader or website scraper implemented. |
| NSE official reference/security reports | Potential dated identity/series evidence; current reference files do not reconstruct past membership | Needs dated classification, availability and symbol/ISIN continuity; no automatic historical backfill | Same official terms apply. **SOURCE_NOT_CLEARED** for ongoing automated ingestion. |
| [NSE corporate-action disclosures](https://www.nseindia.com/companies-listing/corporate-filings-actions) | Potential action descriptions and dated disclosures | Action announcement, ex-date, availability, economic terms and revision evidence differ. No verified complete actionable feed established. | Same terms; **SOURCE_NOT_CLEARED**. Do not invent adjustment factors, dividends or terminal values. |

Only small public Hugging Face metadata/card and official terms/report descriptions
were inspected. No new market-price payload was acquired. The metadata SHA256 is
`23858ccc54d4326c4abeed4d27e20eeb504ada83dae4e55a69081b4c3728fd15`.
The newer 2026 native file is advertised as 14,384,487 bytes with publisher LFS
SHA256 `764bb7c13882bcc4f5195b0523730590347d7c7a1c7278336034235733231eaf`;
that is remote metadata, **not local price/checksum verification**.

## Activation requirements

Establish permission for ongoing automated access, retention and non-commercial
research, including relevant upstream restrictions; independently verify an actual
new complete release and its bytes, dated identities/calendar, action limitations,
receipt chronology, model schema/preprocessing compatibility and inference
authorization. Public accessibility or metadata freshness alone cannot pass this
gate. The implemented check uses the fixed documented public Hugging Face metadata
API over HTTPS, three bounded attempts, ten-second timeouts and backoff. It never
downloads prices or changes clearance. See [official HF download documentation](https://huggingface.co/docs/hub/datasets-downloading).

Approved pinned historical replay remains REAL_MARKET_OBSERVATIONS / RESEARCH_ONLY /
FINAL_VINTAGE_RESEARCH_ASSUMPTION. No production approval follows. Genuine daily
source acquisition and scheduling remain blocked; TEST_ONLY software checks are
not daily-market activation evidence.
