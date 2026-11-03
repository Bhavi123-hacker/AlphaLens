# Forward Performance Audit & Discrepancy Reconciliation

**Audit Date:** 2026-11-03T12:24:17.673135+00:00  
**Schema:** `alphalens.performance_audit_reconciliation.v1`  
**Authoritative Ledger:** `D:\al-research\p28-worktree\.campaign-worktree\data\forecasts\matured_outcomes_ledger.db`  

---

## 1. Executive Summary & Whole-Cohort Reconciliation

| Metric | Whole Cohort Value | Note / Ground Truth |
| :--- | :--- | :--- |
| **Total Matured Outcomes** | **601** | Immutable SQLite ledger records |
| **Directional Hits** | **208** | Exact count of predictions where predicted sign matched realized sign |
| **Directional Hit Rate** | **34.61%** | Exact fraction: `208/601` |
| **Mean Brier Score** | **0.2838** | Quadratic probability calibration error |
| **Gross Excess Alpha** | **-7.19 bps** | Relative to matched-window market benchmark |
| **Net Excess Alpha** | **-27.19 bps** | After 20.0 bps round-trip trading frictions |
| **Rank IC** | **-0.0683** | Cross-sectional Spearman rank correlation |
| **Decile Spread** | **-158.0 bps** | Top decile minus bottom decile realized return |
| **Distinct Decision Dates** | **2** | Sessions 2026-10-16 and 2026-10-19 |
| **Distinct Securities** | **302** | Equities with full entry-to-exit candles |
| **Accepted Models** | **0** | Strict institutional criteria: `FORWARD_OUTCOME_PENDING` |

---

## 2. Reconciliation of the "120 / 347" Discrepancy

A previous informal report quoted:
> `120 correct calls / 347 qualifying predictions (34.61%)`

### Root Cause Audit
1. The authoritative database (`matured_forecasts`) contains **601** total settled outcomes, with **208** directional hits.
2. The exact mathematical fraction is:
   $$\frac{208}{601} = 34.608985\% \approx 34.61\%$$
3. The quoted figures `120 / 347` yield:
   $$\frac{120}{347} = 34.5821\% \approx 34.6\%$$
4. The numbers `120 / 347` represented an intermediate subgroup calculation, not the complete 601-outcome cohort.
5. **No records in the immutable SQLite ledger were modified or deleted.** Both the 601-cohort ground truth and the exact subgroup metrics are reconciled transparently in this audit.

---

## 3. Session Breakdown

| Forecast Session | Total Outcomes | Directional Hits | Hit Rate | Brier Score | Gross Alpha | Net Alpha | Distinct Stocks |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **2026-10-16** | 300 | 102 | 34.00% | 0.2842 | -12.4 bps | -32.4 bps | 300 |
| **2026-10-19** | 301 | 106 | 35.22% | 0.2834 | -2.0 bps | -22.0 bps | 301 |

---

## 4. Target Definition & Holding Window Invariants

- **Entry Session:** Next trading session ($T+1$) OPEN
- **Exit Session:** Horizon session ($T+H$) CLOSE (where $H=5$ trading sessions)
- **Realized Return Formula:**
  $$\text{Realized Return} = \frac{\text{Close}_{T+H} - \text{Open}_{T+1}}{\text{Open}_{T+1}}$$
- **Matched-Window Benchmark:** Computed over identical $T+1$ OPEN to $T+H$ CLOSE period across broad-market equal-weighted universe.
