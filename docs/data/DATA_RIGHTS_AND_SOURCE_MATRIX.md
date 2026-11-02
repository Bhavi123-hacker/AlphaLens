# AlphaLens Data Rights and Source Authorization Matrix

This document defines the formal legal, technical, and operational permissions for all financial market data sources evaluated or integrated into AlphaLens.

**Core Mandate**: A publicly downloadable file is not automatically licensed for automated harvesting, indefinite retention, machine learning training, or redistribution. AlphaLens enforces fail-closed data-rights verification across all pipelines.

---

## 1. Source Rights & Permitted Usage Matrix

| Source Identity | Access Method | Current Clearance | Internal Quota / Budget | Permitted Retention | ML Training Clearance | GitHub Commit Permitted | Operational Enforcement |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Upstox Market Quote API** | Authenticated HTTPS REST (`/historical-candle/`) | **AUTHORIZED (Private V1 Cohort)** | 1,800 GETs/day (internal limit), 600 GETs/run, 60-min cooldown | Durable local encrypted cache (`.local-data`) | Approved for frozen V2 feature inference | **STRICTLY FORBIDDEN** (credentials, raw candles, or proprietary feeds) | Pinned token validator, NTP clock guard (`MAX_WIDTH <= 100 ms`), rate ledger |
| **Official NSE CM-UDiFF Bhavcopy** | Offline operator-supplied file (`BhavCopy_NSE_CM_*.csv.zip`) | **OFFLINE PARSER VERIFIED**; Automated collection **UNAUTHORIZED** | N/A (operator manual download) | Local processing only | Permitted only with verified corporate-action coverage | **FORBIDDEN** (raw exchange data) | Parser in `workers/nse_market/bulk_eod.py`; automated scheduler disabled |
| **Official BSE CM-UDiFF Bhavcopy** | Offline operator-supplied file (`BhavCopy_BSE_CM_*.csv.zip`) | **OFFLINE PARSER VERIFIED**; Automated collection **UNAUTHORIZED** | N/A (operator manual download) | Local processing only | Blocked by domain gate (`BSE_DOMAIN_MODEL_NOT_VALIDATED`) | **FORBIDDEN** (raw exchange data) | Parser in `workers/nse_market/bulk_eod.py`; isolated from NSE model |
| **Official BSE Classic Equity Bhavcopy** | Offline operator-supplied file (`EQ*.CSV.ZIP`) | **OFFLINE PARSER VERIFIED**; Automated collection **UNAUTHORIZED** | N/A (operator manual download) | Local processing only | Blocked by domain gate (`BSE_DOMAIN_MODEL_NOT_VALIDATED`) | **FORBIDDEN** (raw exchange data) | Header validator (`SC_CODE`, `ISIN_CODE`, `SC_GROUP`); group filter |
| **Synthetic Test Fixtures** | Local mock generators | **FULLY AUTHORIZED** | Unlimited local execution | Committed in repository | Permitted for unit/integration tests only | **PERMITTED** (`tests/fixtures/`) | `pytest` test suite, isolated `--basetemp` |
| **Upstox Daily BOD Instrument Master** | Public gzipped JSON (`complete.json.gz`) | **AUTHORIZED (Read-Only Identity Discovery)** | 1 download per daily startup session | Temporary in-memory / local snapshot | Catalog search and ISIN mapping only | **FORBIDDEN** (raw dump); Hash committed | SHA-256 fingerprinting, ordinary equity filter (`INE*01*`) |

---

## 2. Quota Reservation & Fair Usage Policy

1. **Internal 1,800 Daily Request Budget**:
   - The 1,800 requests/day limit is AlphaLens's internal research reservation policy (decisions D95, D97, D100).
   - Unused requests from earlier batches **cannot** be freely reallocated to ad-hoc or unapproved universe scraping.
   - Every scheduled collection run consumes at most 600 reserved requests (250 stocks × 2 sessions if backfilling), enforcing a mandatory 60-minute hardware cooldown between runs.

2. **Automated Scraping Prohibition**:
   - AlphaLens does **not** employ rotating proxies, headless browser scrapers, CAPTCHA bypasses, or undocumented API endpoints.
   - If an exchange portal blocks requests or requires interactive session authentication, the pipeline immediately fails closed with `SOURCE_AUTHENTICATION_OR_ACCESS_RESTRICTED`.

---

## 3. Corporate Action Normalization Rights & Invariants

Exchange Bhavcopy files report raw, unadjusted trade-session settlement prices. In contrast, predictive ML models require continuous, dividend/split/bonus-adjusted series to prevent artificial return shocks.

AlphaLens enforces the following invariants in `workers/nse_market/bulk_eod.py`:
1. **No Imputed Clean History**: An empty supplied corporate action file does **not** prove the absence of corporate actions. A verified `CorporateActionCoverage` certificate signed with the cryptographic hash of the master action ledger is mandatory.
2. **Fail-Closed Model Admission**: If corporate action coverage is unverified or expired for any ISIN, the security's rows remain marked `corporate_action_status="UNVERIFIED_ACTION_COVERAGE_UNQUALIFIED_FOR_ADJUSTED_MODEL"` and `model_compatible=False`.
3. **Volume Inversion Policy**: When applying a split adjustment factor $f$ to price ($P_{adj} = P_{raw} \times f$), trading volume is adjusted by the reciprocal ($V_{adj} = \text{round}(V_{raw} / f)$) to preserve economic turnover.

---

## 4. Privacy & Git Distribution Boundaries

The following assets are strictly categorized as **Private Local Research Assets** and are excluded from Git via `.gitignore`:
- Active PostgreSQL 17 cluster directories (`.local-data/postgres*`)
- Production SQLite forecast shards (`.local-data/**/experimental-v2-prospective.sqlite3`)
- Upstox API keys, client secrets, and access tokens
- Docker VHDX virtual disks (`D:\AlphaLensStorage\*.vhdx`)
- Historical raw Bhavcopy zip archives
