Current status, 2026-10-08 (D69): **USER-AUTHORIZED NONCOMMERCIAL RESEARCH**.
The user explicitly authorizes pinned TejHQ local acquisition, retention,
validation, training/evaluation, hypothetical backtesting, paper simulation and
derived research. Further source-permission clarification is not required.
REAL_MARKET_OBSERVATIONS / RESEARCH_ONLY; production clearance remains OPEN,
market-data use NOT_CLEARED. This amendment records a project/user risk decision,
not a newly obtained exchange grant. The historical D68 audit below is retained.
17 NSE price and 18 NSE reference originals were acquired and checksum-verified.
See [ingestion report](real-10y-ingestion-report.md) for actual measurements and
separate downstream PIT evidence constraints.

# Real historical NSE research source audit

Audit date: 2026-10-07. Branch: `real-data-10y-training`, created directly from
approved P16 `3634b920e7e1d090b3fbf18af3548afb419e7b71`. P15/P16 PASSED reports,
separate commits, clean baseline, unchanged production gates and absence of P17
work were checked before research. `main` and the source DOCX are protected.

**BLOCKED: no source was approved for the requested zero-cost, broad NSE-equity,
10+ year through 2026 training/evaluation/backtesting scope.** No new market archive
was acquired, no real model was trained, and no P11-P14 policy was recalibrated.
This is a bounded source review, not proof that a qualifying dataset cannot exist.

## Method and decision rule

Reviewed primary dataset cards, repository metadata, explicit licenses and upstream
terms. Public Kaggle metadata endpoints and Hugging Face metadata/file listings
were accessed anonymously; no account, credentials, protected gateway, market-data
API, daily NSE downloader, scraper or anti-bot workaround was used. Website access
errors were recorded as unavailable evidence. Small metadata captures stay ignored
under `data/source-audit-evidence`; committed evidence contains descriptions,
references, metadata SHA256s and publisher file sizes/digests, not price records.

[Machine-readable audit](source-audit.json) contains **35 detailed candidates and
64 additional catalog-only discovery leads**. Every record scores all 15 requested
criteria: observation reality, NSE equity scope, depth, OHLCV, security count,
departures, identity, license, provenance, ML use, download method, reproducibility,
updateability, corporate actions and benchmark. Scores indicate evidence maturity:
0 = absent/unknown/contradictory; 1 = publisher claim; 2 = directly inspected primary
metadata or prior accepted evidence; 3 = previously captured, checksum-verified
artifact measurement. A zero does not prove the underlying information is absent.
These are audit categories, not legal probabilities or a summed approval algorithm.

Data reality and rights are separate fields. Newly inspected prices are only
publisher claims because price files were not acquired. Earlier real Mendeley
observations retain their prior bounded APPROVED_RESEARCH status under D36-D39.
That residual-risk acceptance is preserved; this audit does not demand independent
proof of every upstream right. It does require addressing the specific contrary
terms or scope/provenance gaps found for proposed new sources. An uploader's open
license is positive evidence, not a mechanism to ignore identified contradictions.

## Best coverage candidate: TejHQ Indian Markets

Publisher: TejHQ. [Dataset](https://huggingface.co/datasets/tejhq/indian-markets).
The card claims NSE daily coverage from 2010-01-04 through the current period,
approximately 2,300 instruments/day, EQ/BE/BZ series, OHLCV, ISIN/name/symbol fields,
corporate actions and symbol history. These are publisher claims, not measured
common-equity, departure or session counts. The card acknowledges pre-publication
row removal and derived identity/adjustment handling; those outputs cannot replace
AlphaLens's own PIT evidence. [Pinned card](https://huggingface.co/datasets/tejhq/indian-markets/blob/14d81bbaef8c0f8dc673fb3e3573f9e1f32bed98/README.md).

Public repository revision `14d81bbaef8c0f8dc673fb3e3573f9e1f32bed98` lists
17 NSE price Parquets, one per year 2010-2026, totaling **192,163,454 bytes**.
Those sizes and LFS SHA256s were read from metadata, not verified by downloading.
Exact earliest/latest sessions, rows and coverage remain unmeasured. The audit JSON
pins every path, declared size and digest; actual-download checksums remain null.

Rights decision: **INSUFFICIENT_RIGHTS_EVIDENCE**. The dataset YAML declares MIT;
this is a dataset declaration, not merely an inferred code license. However, the
card body separates its MIT pipeline from exchange-published data and asserts
redistribution without identifying a grant resolving the conditions below. No
infringement finding is asserted. A scoped clarification is needed before approval.

## Specific terms evidence affecting proposed uses

- [NSE terms](https://www.nseindia.com/static/nse-terms-of-use), clauses 8 and 9:
  systematic automated collection is restricted and data use for virtual trading
  or simulation is expressly prohibited. AlphaLens must resolve that condition
  for the requested P10 replay; ordinary public download is not an exception.
- [NSE copyright](https://www.nseindia.com/static/nse-copyright): personal,
  noncommercial or educational download permission includes attribution and
  preservation conditions; it does not establish unrestricted cleaned-data reuse.
- [NSE disclaimer](https://www.nseindia.com/static/nse-disclaimer): research-oriented
  access has institution/organization eligibility conditions, an aggregate 2GB
  threshold and possible NDA/reporting requirements. Eligibility is not assumed.
- [NSE research policy data list](https://nsearchives.nseindia.com/web/sites/default/files/inline-files/Data%20list%20under%20NSE%20Data%20Sharing%20Policy%20for%20Research%20and%20Analysis_20250728.pdf):
  daily reports are included in the research basket; voluminous archives above 2GB
  are separately chargeable. A sub-2GB mirror does not itself grant downstream rights.
- [NSE data usage policy](https://www.nse.in/static/market-data/nse-data-policy):
  research access and its limitations are documented through the applicable
  arrangement. No such arrangement has been established for this sprint.
- [TradingView terms](https://www.tradingview.com/policies/), section 3: market data
  is display-only, with explicit non-display/machine-processing restrictions. The
  TradingView/tvDatafeed datasets below are rejected absent an applicable exception.
- [NSE MCP](https://www.nseindia.com/nse-mcp) expressly withholds AI/model-training
  permission. MCP is rejected and was not used for data acquisition.

[Hugging Face terms](https://huggingface.co/terms-of-service), Your Content,
provide uploader rights representations and public-content licensing, while
preserving accompanying license terms. Its [dataset-card documentation](https://huggingface.co/docs/hub/datasets-cards)
confirms the license metadata describes the dataset. Both are positive evidence;
neither settles the identified NSE source-specific conditions. Existing D36-D39
Mendeley acceptance remains exactly as documented in [the prior source report](research-fixture-source.md).

## Candidate findings

Exact publishers, URLs, declared sizes/updates, provenance, decisions, limitations
and per-criterion scores are in `source-audit.json`; the following provides a
readable index. License names are declarations, not production clearance.

| Candidate | Coverage / license evidence | Decision and limiting evidence |
| --- | --- | --- |
| TejHQ / Hugging Face | 2010-2026 claimed; MIT metadata; NSE raw, actions, identity trees | INSUFFICIENT_RIGHTS_EVIDENCE; resolve source-specific scope; strongest coverage lead. |
| xxparthparekhxx / Hugging Face | 2000-2026 daily claimed, 2,500+ stocks/indices; dataset MIT | INSUFFICIENT_RIGHTS_EVIDENCE; no collection source/entitlement established; Upstox tag alone is not provenance. Repository update January 2026 cannot prove latest October data. |
| vishnun0027 / Hugging Face | Yahoo/yfinance, multi-asset daily updates; MIT | INSUFFICIENT_RIGHTS_EVIDENCE; source disclosed but redistribution scope/PIT/departures unestablished. |
| destinybound / Hugging Face | Apache label, empty repository | REJECTED; no price archive. |
| TickerTruth security master | Identity/action source, roughly 2,400 catalog rows | CONDITIONALLY_USABLE for later metadata review, not a price archive or historical availability proof. |
| Ujjval Patel / Kaggle | 2,000+ stocks, 1990-2025 title; CDLA-Permissive-1.0 | REJECTED; explicitly TradingView/tvDatafeed, contrary non-display terms. |
| automon / Kaggle | 501 current Nifty 500 stocks, daily 1999-2026 claimed; CC0 | REJECTED; TradingView source and current-cohort survivorship. |
| Ishan Sirohi / Kaggle | Current October 2026 NIFTY 200, 2009-2026 Close/Volume; CC0 | REJECTED; missing OHLC and departed names explicitly disclosed, Yahoo adjustments. |
| Hemadri Ahire / Kaggle | Zerodha-labelled ten-year minute history, 40 stocks; MIT | INSUFFICIENT_RIGHTS_EVIDENCE; narrow coverage, unknown entitlement and gap-fill semantics. |
| destinyBound / Kaggle | OHLCV/dividends/splits through October 2023; Apache | INSUFFICIENT_RIGHTS_EVIDENCE; upstream/source start unknown, no 2026 extension. |
| Akshay Pawar / Kaggle | NSE bhavcopy, mixed cash/derivatives assets; CC0, updated 2022 | INSUFFICIENT_RIGHTS_EVIDENCE; exact depth/departures and scoped exchange permission unknown. |
| Yash Yennam / Kaggle | January 2016-December 2024 title; Apache, empty description | INSUFFICIENT_RIGHTS_EVIDENCE; under ten full years, no latest extension or provenance statement. |
| Nikit Periwal / Kaggle | NSE via nsepy/nsetools, 1990-June 2021 claimed; CC0 | INSUFFICIENT_RIGHTS_EVIDENCE; no current extension or grant resolving source terms. |
| Vopani / Kaggle | NIFTY-50 stock histories 2000-April 2021; CC0 | REJECTED for requested broad/PIT universe and current-period scope. |
| Abhishek Yanamandra / Kaggle | 1,000+ Yahoo v7 stock CSVs, updated 2019; CC0 | INSUFFICIENT_RIGHTS_EVIDENCE; upstream scope, latest period and departures missing. |
| Larxel / Kaggle | All-listed claim, updated 2022; CC0 | INSUFFICIENT_RIGHTS_EVIDENCE; collection provenance and exact depth not disclosed. |
| Ramanathan Perumal / Kaggle | 2013-2016 minute data, several websites; CC0 | REJECTED; inadequate depth and mixed unverified source lineage. |
| Mayookh / Kaggle yearly bhavcopies | CC0, 2001-2017 catalog series | INSUFFICIENT_RIGHTS_EVIDENCE; no 2026 extension/scoped source grant. Remaining yearly entries retained as discovery leads. |
| Nandan Patil / Zenodo nser | R software files, not prices | REJECTED as dataset; do not treat software licensing as data permission. |
| Abhay Rana / Zenodo Nemo ISIN DB | Versioned security-type/identity snapshots | CONDITIONALLY_USABLE as identity discovery, not historical OHLCV or backdated classification. |
| Bhagavatula Aruna / Mendeley | Monthly CMIE panel, 1995-2016 | REJECTED; proprietary source scope and wrong frequency. |
| Jaydip Sen/Sidra Mehtab / Mendeley | Short NIFTY index/sentiment study; CC BY | REJECTED; no broad equity archive. |
| Puskal Khana / Mendeley | NIFTY 50 Date/Close 2004-April 2024; CC BY | CONDITIONALLY_USABLE benchmark lead; no Open/2026 coverage, rights scope still needs review. |
| Neeraj Eusebius / Mendeley | FII/index covariates and study outputs 2000-2024; CC BY | REJECTED as security OHLCV archive. |
| Marco Bonelli / Mendeley | Annual SENSEX/macroeconomics 1980-2024 | REJECTED; frequency/exchange/product mismatch. |
| R B / Mendeley monthly_ohlcv | Monthly input; CC BY, source/range unclear | REJECTED; daily NSE scope unestablished. |
| Tawade/Kulkarni / Mendeley, five prior datasets | Captured real single-security CSVs, CC BY | APPROVED_RESEARCH for existing bounded D36-D39 fixture scope only; not broad/latest/PIT sprint approval. |
| Venkata Ramareddy / GitHub pipeline | 2015-2026 title, MIT software, raw files absent | INSUFFICIENT_RIGHTS_EVIDENCE; no usable licensed data archive; estimated adjustment factors must not be imported. |
| Dr-Kitz28 / GitHub | Research-only description, all-stock claim | INSUFFICIENT_RIGHTS_EVIDENCE; source/data license/depth not established. No prices downloaded. |
| Official NSE archives | Authoritative price/reference/action reports | CONDITIONALLY_USABLE only through permitted manual or expressly authorized research delivery. |
| Official NSE MCP | Five-year advertised access | REJECTED for training and depth. |
| Government/university/institutional discovery | OGD India, papers and repository search | INSUFFICIENT_RIGHTS_EVIDENCE; no identified qualifying broad daily archive; not proof of nonexistence. |

No constructed benchmark is called NIFTY 50. Fundamentals stay UNAVAILABLE.
Absence from a last-session file cannot be equated to delisting. EQ is not proof
of COMMON_EQUITY; ETFs/REITs/INVITs/debt/funds require P4 evidence. No current
constituent list was projected backward. No real price/feature/label profile was
computed before permission; downstream machine files explicitly report NOT_RUN.

## Exact next actions

See [the prepared request and conditional acquisition instructions](real-data-access-request.md).
Two possible routes exist: obtain a source-specific clarification/grant for the
best coverage candidate, or use NSE's eligible academic-research request process.
No message, account signup, terms acceptance or purchase was performed for the user.
An actual zero-cost grant is needed; a potential waiver is not guaranteed free access.
Downloading a questionable file alone does not clear its rights gate.

On approval, source files must enter P2 immutable raw capture before parsing; then
P3 quality, P4 dated identities/type/universe/calendar, P5 canonical vintages,
P6 features and P7 maturity/alignment. Missing publication/schedule/action facts
remain unknown. P8/P9/P10 must consume their existing contracts, not a notebook
join. P11-P14 recalibration and P17 remain outside scope.

REAL DATA SPRINT BLOCKED — NO APPROVED ZERO-COST 10+ YEAR SOURCE FOUND.
