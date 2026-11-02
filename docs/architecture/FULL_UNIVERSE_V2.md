# AlphaLens Full Universe Architecture (V2)

This document specifies the end-to-end architecture of AlphaLens for supporting all 8,169 verified NSE and BSE ordinary equity listings while preserving strict resource, data integrity, and model isolation boundaries.

---

## 1. System Topology & Tiered Pipeline

AlphaLens decomposes market research into four strictly decoupled tiers. Downstream tiers never infer or fabricate state from upstream tiers.

```
┌────────────────────────────────────────────────────────────────────────┐
│                      TIER 1: SEARCHABLE CATALOG                        │
│   8,169 Ordinary Equities (3,214 NSE_EQ + 4,955 BSE_EQ across 5,664 ISINs) │
│   - Verified INE*01* Ordinary ISINs with Luhn checksum validation     │
│   - Fast in-memory / SQLite prefix search & identity resolution       │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Approved 500-Stock Cohort Filter
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   TIER 2: REAL DAILY MARKET STORE                      │
│   451,468 Retained Real Daily Candles across 500 Research Equities     │
│   - PostgreSQL 17 Canonical Storage + Compressed Parquet Historical    │
│   - Strict NTP Clock-Gated Acquisition (MAX_WIDTH <= 100 ms)           │
│   - Daily Ingestion at 20:30, 21:30, 22:30 IST (1,800 GET budget)      │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Warmup & Liquidity Screening
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                      TIER 3: FEATURE PIPELINE                          │
│   16-Dimensional Point-in-Time Numerical Feature Matrix               │
│   - 315 Eligible NSE Equities (185 excluded: warmup / liquidity)      │
│   - Split/Bonus Adjusted Prices via Verified Corporate Action Factors  │
│   - Strict Domain Gate: BSE Equities Gated (BSE_DOMAIN_NOT_VALIDATED) │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Frozen V2 / Multi-Model Inference
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                  TIER 4: DURABLE FORECAST LEDGER                       │
│   1,876 Immutable Forecast Records across 190 Partitioned SQLite Shards│
│   - Unique (model_id, instrument_key, session) Decision Lineage       │
│   - Prospective-Only Evaluation (Zero Backdating / Matured Outcomes)   │
│   - Research Dashboard Top 5, Top 10, Top 20 Candidate Generation      │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Universal Identity & Listing Separation

A common pitfall in Indian equity analysis is conflating company identity with exchange listing identity. AlphaLens enforces the following rules:
1. **Exchange-Prefixed Instrument Keys**: Every listing has a unique canonical key (`NSE_EQ|INE...` or `BSE_EQ|INE...`). Even when a company trades on both NSE and BSE under the same ISIN (5,664 unique ISINs vs 8,169 listings), prices, order book dynamics, and volume are **never** mixed.
2. **Ordinary Equity Filter**:
   - ISIN must begin with `INE` and have `01` as characters 8–9 (`INE*01*`).
   - Preference shares (`04`), debt (`07`), mutual funds (`08`), and ETFs (`09`) are rejected at discovery.
   - NSE series must belong to `{"EQ", "BE", "BZ", "SM"}`; BSE series must belong to approved common groups (`A`, `B`, `T`, `X`, `M`, etc.).

---

## 3. Storage Optimization for Bounded Disk (~20 GB Free Space)

To prevent unbounded disk consumption as historical data scales, AlphaLens implements:
- **Canonical Parquet Partitions**: Daily candles are compressed using Snappy/ZSTD-compressed columnar Parquet, achieving ~8.2 bytes per bar versus ~180 bytes in uncompressed JSON.
- **Streaming Feature Extraction**: Feature transforms operate on sliding historical windows without holding the full 5-year universe in RAM.
- **Partitioned SQLite Forecast Shards**: Forecast records are sharded by the first two hexadecimal digits of the instrument digest (`expanded-forecasts/<xx>/experimental-v2-prospective.sqlite3`), bounding write locks and database file sizes to <10 MB per shard.
- **Strict 8 GiB Floor Guard**: Every pipeline task checks available disk space before starting; if free space drops below 8 GiB, the job safely aborts with `INSUFFICIENT_DISK_SAFETY_RESERVE`.

---

## 4. Multi-Model Architecture & Acceptance Protocol

The modeling subsystem supports six model families with distinct operational status:
1. **Logistic Regression (Classification)**: L2 regularized, standard scaled baseline.
2. **Random Forest Classifier (Classification)**: 32 trees, max depth 4, min samples leaf 3.
3. **Histogram Gradient Boosting (Classification)**: Fast histogram-binned gradient boosting.
4. **Ridge Regression (Regression)**: L2 regularized return predictor.
5. **Histogram Gradient Boosting (Regression)**: Non-linear regression for 1, 5, 10, 20-session return prediction.
6. **CPU-Bounded Sequence LSTM (Deep Learning)**: 1 recurrent layer ($8 \to 16$), dropout 0.1, dense output, evaluated on CPU via NumPy matrix multiplications.

Every model candidate is evaluated using strict chronological walk-forward splits with a 20-trading-session embargo to prevent label leakage.
