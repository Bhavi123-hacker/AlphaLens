# AlphaLens BSE Domain Validation & Model Isolation Policy

This document defines the technical, statistical, and operational requirements for evaluating Bombay Stock Exchange (BSE) equities and establishes why transferring NSE-trained models directly to BSE is strictly prohibited under `BSE_DOMAIN_MODEL_NOT_VALIDATED`.

---

## 1. The BSE Domain Shift Problem

While 4,955 BSE ordinary equities are indexed and searchable in the AlphaLens catalog, they cannot be served using NSE-trained predictive models due to substantial structural domain differences:

```
┌───────────────────────────────────────┬───────────────────────────────────────┐
│               NSE DOMAIN              │               BSE DOMAIN              │
├───────────────────────────────────────┼───────────────────────────────────────┤
│ High liquidity concentration (Nifty500│ Long tail of 3,000+ illiquid microcaps│
│ accounts for >90% of daily volume)    │ (Group T, X, Z with zero volume days) │
├───────────────────────────────────────┼───────────────────────────────────────┤
│ Tight bid-ask spreads (1–5 bps on EQ) │ Wide spreads (50–500 bps on B/T/Z)    │
├───────────────────────────────────────┼───────────────────────────────────────┤
│ Uniform series: mostly EQ, BE         │ Fragmented groups: A, B, T, X, M, Z   │
├───────────────────────────────────────┼───────────────────────────────────────┤
│ Order book continuous matching        │ Periodic call auctions on trade-to-   │
│                                       │ trade segments                        │
├───────────────────────────────────────┼───────────────────────────────────────┤
│ Verified split/bonus adjustment feeds │ Fragmented corporate action filings   │
└───────────────────────────────────────┴───────────────────────────────────────┘
```

Applying an NSE-fitted gradient boosted tree or linear model to an illiquid BSE stock produces catastrophic failure modes:
1. **Bid-Ask Bounce Artifacts**: Illiquid stocks oscillating between bid and ask prices trigger artificial mean-reversion and momentum signals.
2. **Execution Slippage**: A predicted 50 bps return is wiped out by a 200 bps effective spread.
3. **Survivorship Bias**: Frequent suspensions and group reclassifications (e.g. transfer to `Z` or `P` group) invalidate historical feature stationarity.

---

## 2. Structural Group & Liquidity Screening

BSE Bhavcopy entries partition securities into groups. AlphaLens restricts ordinary equity candidates to verified groups:
- **Eligible Common Groups**: `A` (Leading liquid), `B` (Mid-cap/Active), `T` (Trade-to-trade), `X` / `XT` (Over-the-counter list), `M` / `MT` (SME segment).
- **Ineligible Groups**: `Z` (Non-compliant/defaulter), `P` (Physical shares only), `F` (Fixed income), `E` (ETFs).

### Empirical Liquidity Gate
Before any BSE equity can enter feature generation, it must pass a 60-trading-day liquidity filter:
- Non-zero trading volume on $\ge 90\%$ of market sessions.
- Average daily turnover $\ge ₹1,000,000$.
- No active circuit breaker locks on $>20\%$ of sessions.

---

## 3. Dedicated BSE Training Pipeline Architecture

To establish an independently validated BSE predictive track, AlphaLens specifies:
1. **BSE-Specific Training Data**:
   - Historical prices sourced exclusively from BSE UDiFF (`BhavCopy_BSE_CM_*.csv.zip`) or verified classic Bhavcopies (`EQ*.CSV.ZIP`).
   - Corporate actions verified through BSE corporate action notices with explicit `CorporateActionCoverage` certificates.
2. **Domain-Specific Feature Engineering**:
   - Inclusion of spread proxies (Corwin-Schultz high-low spread estimator).
   - Liquidity-adjusted volume features (Amihud illiquidity ratio).
3. **Separate Model Registry**:
   - Model versions tagged `bse.v1.*` with independent SHA-256 manifests.
   - Dedicated forecast ledger shard under `expanded-forecasts/bse/`.
   - Separate prospective evaluation ledger requiring its own 126 forward decision dates and 1,000 matured outcomes.

---

## 4. Current Status: Gated Fail-Closed

Until a dedicated BSE training corpus is fully ingested and passes independent acceptance:
- All BSE equities remain searchable in the AlphaLens explorer.
- In all research and scoring views, BSE equities display:
  `ml_gate: "BSE_DOMAIN_MODEL_NOT_VALIDATED"`
  `model_compatible: false`
- No speculative or unvalidated predictions are ever published for BSE stocks.
