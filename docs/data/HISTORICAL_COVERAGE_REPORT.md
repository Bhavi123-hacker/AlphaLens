# AlphaLens 4-Tier Universe and Historical Coverage Report

This document reports the exact, independently verified data coverage across all four operational tiers of AlphaLens on **3 November 2026**.

**Integrity Mandate**: AlphaLens clearly distinguishes between Universal Search (8,169 ordinary listings), Retained Real Market Data (500 approved cohort stocks), Model-Compatible Features (315 eligible NSE stocks), and Immutable Forecasts (1,876 ledger records).

---

## 1. 4-Tier Coverage Summary

| Pipeline Tier | Item Scope | Exact Verified Count | Breakdown / Identifiers | Active Verification Source | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Tier 1: Searchable Catalog** | Common Ordinary Equities | **8,169 listings** | **3,214 NSE** equities<br>**4,955 BSE** equities<br>**5,664 unique company ISINs** | Upstox Daily BOD Master (`complete.json.gz`), SHA-256: `31fa7f6b...` | **VERIFIED & SEARCHABLE** |
| **Tier 2: Real Daily Market Data** | Retained Historical Candles | **451,468 candles** | **500 cohort equities**<br>Latest session: **2026-11-02**<br>**498 received / 2 pending vendor** | PostgreSQL 17 canonical store + compressed Parquet (`.local-data`) | **VERIFIED & OPERATIONAL** |
| **Tier 3: Model-Compatible Features** | Evaluated Feature Vectors | **315 eligible stocks** | **315 qualified NSE equities**<br>**185 excluded cohort stocks**<br>**0 BSE equities** (domain-gated) | Point-in-time feature matrix (`scores-latest.json`), 16 dimensions | **FROZEN V2 INFERENCE READY** |
| **Tier 4: Durable Forecast Ledger** | Immutable Future Forecasts | **1,876 records** | **315 latest session forecasts**<br>**1,845 unique decisions**<br>**190 partitioned SQLite shards** | SQLite shards (`expanded-forecasts/**/experimental-v2-prospective.sqlite3`) | **PROSPECTIVE ACTIVE** |

---

## 2. Tier 1: Searchable Ordinary Equity Universe (8,169 Listings)

The catalog covers all genuine ordinary equity listings traded on Indian exchanges:
- **Filtering Pipeline**:
  - Total initial BOD records inspected: 120,700
  - Total cash equities discovered: 9,866 (NSE) + 13,117 (BSE)
  - Exclusion of non-ordinary instruments:
    - Debt, preference shares, and mutual funds (`INE*04*`, `INE*07*`, `INE*08*`): 7,538 rejected
    - Exchange-traded funds (ETFs): 971 rejected
    - Non-common trading series (Rights, Warrant, Block): 6,290 rejected
    - Differential voting rights (DVR) non-ordinary shares: 14 rejected
    - Malformed ISIN checksum: 1 rejected
  - **Net Searchable Common Equities**: **8,169 listings** across **5,664 distinct corporate ISINs**.

Every one of the 8,169 listings is searchable in the local UI by company name, exchange symbol, or ISIN.

---

## 3. Tier 2: Real Daily Market Data Store (500 Stocks, 451,468 Candles)

- **Approved Collection Cohort**: 500 liquid NSE ordinary equities approved under research authorization.
- **Latest Validated Session**: **2 November 2026**.
- **Session Receipt**:
  - Valid candles received: **498 / 500** (99.6% session delivery).
  - Pending vendor publication: **2 stocks** (`NSE_EQ|INE023A01030` and `NSE_EQ|INE029L01018`).
- **Cumulative Retained History**: **451,468 verified daily bars** dating back across up to 10 years of historical data.

---

## 4. Tier 3: Feature Pipeline Eligibility (315 Stocks vs 185 Exclusions)

A security having historical candles does not automatically qualify it for predictive machine learning. Out of the 500 cohort equities:
- **315 Equities Qualified**: Full 60-session historical warmup available, zero NaN feature entries, finite volatility and ATR measures, and verified corporate action continuity.
- **185 Equities Excluded**:
  1. *Insufficient Warmup*: 142 equities had recent listing dates or missing bars within the trailing 60 sessions, preventing calculation of 20-day momentum and 14-day RSI.
  2. *Low Liquidity / Trading Halts*: 38 equities experienced trading halts or circuit-breaker locks during the warmup window.
  3. *Pending Corporate Action Proof*: 5 equities underwent share restructuring without verified post-event corporate action adjustment factors.

---

## 5. Tier 4: Durable Forecast Ledger (1,876 Records)

All prospective model forecasts are stored in append-only SQLite databases sharded by the security's ISIN hash prefix:
- Total immutable forecast records: **1,876**.
- Unique `(model_id, instrument_key, session)` decisions: **1,845**.
- Latest 2 November session forecasts: **315**.
- Outcome revisions: **0** (immutable audit trail; no retrospective overwrites permitted).
