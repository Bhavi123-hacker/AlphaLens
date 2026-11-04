# AlphaLens — Automated Model Acceptance & Strategy Performance Audit

**Evaluated At:** 2026-11-04T17:52:34.283904+00:00  
**Ledger Inspected:** `D:\al-research\p28-worktree\.campaign-worktree\data\forecasts\matured_outcomes_ledger.db`  
**Acceptance Verdict:** **ACCEPTANCE_EVIDENCE_QUARANTINED**  
**Independently Approved Models:** **0 / 20**

---

## 1. Strategy Performance After Costs (20 bps Roundtrip)

| Metric | Value | Threshold | Status |
| :--- | :--- | :--- | :--- |
| Gross Return | -0.0436 | — | Evaluated |
| Net Return | -0.0456 | — | After 20 bps |
| Benchmark Return | -0.0429 | — | Broad Market |
| Gross Alpha | -7.2 bp | > 0 | Done |
| Net Alpha | -27.2 bp | > 0 | Done |
| Hit Rate | 34.6% | > 54% | Done |
| Brier Score | 0.2838 | <= 0.25 | Done |
| Rank IC | -0.0683 | > 0.02 | Done |
| Decile Spread | -158 bp | > 0 | Done |

---

## 2. Independent Model Acceptance Criteria Progress

| Requirement | Required | Current | Status |
| :--- | :--- | :--- | :--- |
| Forward Dates | >= 126 | 2 | In Progress |
| Qualified Outcomes | >= 1,000 | 0 | In Progress |
| Distinct Securities | >= 30 | 302 | PASS |
| Directional Hit Rate | > 54.0% | 34.61% | Evaluated |
| Net Alpha After Friction | > 0.0 bps | -27.19 bps | Evaluated |
| Brier Calibration | <= 0.25 | 0.2838 | Evaluated |
| Cross-Model Pooling | Prohibited | Enforced | PASS |

---

## 3. Policy & Governance Statement

Quarantined forward outcomes (601) contribute ZERO observations and ZERO decision dates to independent ML acceptance.
