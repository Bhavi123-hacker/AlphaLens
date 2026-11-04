# Forward Performance Audit & Discrepancy Reconciliation

**Audit Date:** 2026-11-04T08:19:41.414600+00:00
**Schema:** `alphalens.performance_audit_reconciliation.v1`
**Authoritative Ledger:** `D:\al-research\p28-worktree\.campaign-worktree\data\forecasts\matured_outcomes_ledger.db`

---

## 1. Executive Summary & Whole-Cohort Reconciliation

| Metric | Whole Cohort Value | Note / Ground Truth |
| :--- | :--- | :--- |
| **Total Matured Outcomes** | **601** | Immutable SQLite ledger records |
| **Directional Hits** | **208** | Predictions where predicted sign matched realized |
| **Directional Hit Rate** | **34.61%** | Exact fraction: `208/601` |
| **Mean Brier Score** | **0.2838** | Quadratic calibration error |
| **Gross Alpha** | **-7.19 bps** | Benchmark-relative |
| **Net Excess Alpha** | **-27.19 bps** | After 20bps friction |
| **Rank IC** | **-0.0683** | Cross-sectional Spearman rank |
| **Decile Spread** | **-158.0 bps** | Top minus bottom decile |
| **Distinct Decision Dates** | **2** | Oct 16 and Oct 19 |
| **Distinct Securities** | **302** | Equities with full candles |
| **Accepted Models** | **0** | Gated under `ACCEPTANCE_EVIDENCE_QUARANTINED` |

---

## 2. Model Acceptance Quarantine Status

- **Quarantine Active:** `True`
- **Quarantined Outcomes:** `601`
- **Qualified Acceptance Outcomes:** `0`
- **Qualified Acceptance Decision Dates:** `0`
- **Acceptance Status:** `ACCEPTANCE_EVIDENCE_QUARANTINED`
- **Quarantine Policy:** Quarantined outcomes contribute ZERO observations
  and ZERO decision dates to independent ML acceptance.

---

## 3. Reconciliation of the "120 / 347" Discrepancy

A previous informal report quoted:
> `120 correct calls / 347 qualifying predictions (34.61%)`

### Root Cause Audit
1. The authoritative database contains **601** total settled outcomes, with **208** hits.
2. The exact mathematical fraction is:
   $$\frac{208}{601} = 34.608985\% \approx 34.61\%$$
3. The quoted figures `120 / 347` yield:
   $$\frac{120}{347} = 34.5821\% \approx 34.6\%$$
4. The numbers `120 / 347` represented an intermediate subgroup calculation.
5. **No records in the immutable ledger were modified or deleted.**
